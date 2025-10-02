import json
from googleapiclient.errors import HttpError

from pypika import functions
from pypika.terms import ExistsCriterion

import frappe
from frappe import _
from frappe.desk.reportview import get_filters_cond
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.integrations.doctype.google_calendar.google_calendar import get_google_calendar_object, format_date_according_to_google_calendar
from frappe.query_builder.custom import ConstantColumn

from frappe.utils import (
	get_fullname,
	now_datetime,
	get_datetime,
	add_to_date,
	flt,
	getdate,
	cint,
	time_diff_in_seconds,
)

from erpnext.crm.doctype.appointment.appointment import Appointment as BaseAppointment

class Appointment(BaseAppointment):
	def __setup__(self):
		self.flags.update_related_appointments = True

	def create_calendar_event(self):
		pass

	def validate(self):
		if not self.scheduled_time:
			self.scheduled_time = now_datetime()

		# if start == end this scenario doesn't make sense i.e. it starts and ends at the same second!
		hours_to_add = flt(frappe.db.get_single_value("Appointment Booking Settings", "custom_default_travel_hours"))
		if not self.custom_ends_on:
			for row in self.custom_appointment_services:
				hours_to_add += flt(row.working_hours)
			self.custom_ends_on = add_to_date(self.scheduled_time, hours=hours_to_add)

		if self.scheduled_time and self.custom_ends_on:
			self.validate_from_to_dates("scheduled_time", "custom_ends_on")

		if self.custom_sync_with_google_calendar and not self.custom_google_calendar:
			frappe.throw(_("Select Google Calendar to which event should be synced."))

	def before_save(self):
		self.set_party_email()

	def on_update(self):
		self.sync_communication()
		if self.flags.update_related_appointments:
			self.update_all_related_appointments()

	def update_all_related_appointments(self):
		if cint(frappe.db.get_single_value("Appointment Booking Settings", "custom_reschedule_all_linked_appointments")) == 0:
			return
		if self.status != 'Closed':
			return
		# check if ends time is updated and status is closed
		prev_doc = self.get_doc_before_save()
		if not prev_doc:
			return
		time_diff = time_diff_in_seconds(self.custom_ends_on, prev_doc.custom_ends_on)
		if (time_diff == 0) or prev_doc.status == 'Closed':
			return
		
		Appointment = frappe.qb.DocType("Appointment")
		query = (
			frappe.qb.from_(Appointment)
			.select(Appointment.name)
			.where(
				(Appointment.custom_employee == self.custom_employee)
				& (Appointment.name != self.name)
				& (Appointment.status == 'Open')
				& (Appointment.scheduled_time >= self.custom_ends_on)
				& (functions.Date(Appointment.scheduled_time) == getdate(self.custom_ends_on))
			)
		)
		appointments = query.run(as_dict=True)
		if len(appointments) == 0:
			return
		for appointment in appointments:
			appointment = frappe.get_doc("Appointment", appointment)
			
			appointment.flags.update_related_appointments = False
			appointment.scheduled_time = add_to_date(appointment.scheduled_time, seconds=time_diff)
			appointment.custom_ends_on = add_to_date(appointment.custom_ends_on, seconds=time_diff)
			appointment.flags.ignore_permissions = True
			appointment.flags.ignore_mandatory = True
			appointment.save()



	def on_trash(self):
		communications = frappe.get_all(
			"Communication",
			filters={"reference_doctype": self.doctype, "reference_name": self.name},
			pluck="name",
		)
		for communication in communications:
			frappe.delete_doc("Communication", communication, force=True)

	def sync_communication(self):
		event_participants = []
		if self.custom_employee:
			p1 = frappe._dict()
			p1.update({
				"reference_doctype": "Employee",
				"reference_docname": self.custom_employee,
			})
			event_participants.append(p1)
		
		if self.appointment_with and self.party:
			p1 = frappe._dict()
			p1.update({
				"reference_doctype": self.appointment_with,
				"reference_docname": self.party,
			})
			event_participants.append(p1)

		if not event_participants:
			return

		for participant in event_participants:
			if communications := frappe.get_all(
				"Communication",
				filters=[
					["Communication", "reference_doctype", "=", self.doctype],
					["Communication", "reference_name", "=", self.name],
					["Communication Link", "link_doctype", "=", participant.reference_doctype],
					["Communication Link", "link_name", "=", participant.reference_docname],
				],
				pluck="name",
				distinct=True,
			):
				for comm in communications:
					communication = frappe.get_doc("Communication", comm)
					self.update_communication(participant, communication)
			else:
				meta = frappe.get_meta(participant.reference_doctype)
				if hasattr(meta, "allow_events_in_timeline") and meta.allow_events_in_timeline == 1:
					self.create_communication(participant)

	def create_communication(self, participant: "EventParticipants"):
		communication = frappe.new_doc("Communication")
		self.update_communication(participant, communication)
		self.communication = communication.name

	def update_communication(self, participant: "EventParticipants", communication: "Communication"):
		communication.communication_medium = "Event"
		communication.subject = self.custom_subject
		communication.content = self.customer_details if self.customer_details else self.custom_subject
		communication.communication_date = self.scheduled_time
		communication.sender = self.owner
		communication.sender_full_name = get_fullname(self.owner)
		communication.reference_doctype = self.doctype
		communication.reference_name = self.name
		communication.communication_medium = "Meeting"
		communication.status = "Linked"
		communication.add_link(participant.reference_doctype, participant.reference_docname)
		communication.save(ignore_permissions=True)


	def set_party_email(self):
		if self.appointment_with and self.party:
			party_contact = get_default_contact(
				self.appointment_with, self.party
			)
			email = (
				frappe.get_value("Contact", party_contact, "email_id") if party_contact else None
			)
			self.customer_email = email

	def after_insert(self):
		insert_event_in_google_calendar(self)


@frappe.whitelist()
def get_appointments(start, end, user=None, for_reminder=False, filters=None) -> list[frappe._dict]:
	if not user:
		user = frappe.session.user

	if isinstance(filters, str):
		filters = json.loads(filters)

	filter_condition = get_filters_cond("Appointment", filters, [])

	tables = ["`tabAppointment`"]
	if "`tabAppointment Participants`" in filter_condition:
		tables.append("`tabAppointment Participants`")
	Appointment = frappe.qb.DocType("Appointment")
	DocShare = frappe.qb.DocType("DocShare")
	
	share_query = ExistsCriterion(
					frappe.qb.from_(DocShare)
					.select(1)
					.where(
						(DocShare.share_doctype == "Appointment")
						& (DocShare.share_name == Appointment.name)
						& (DocShare.user == user)
					)
        )
	query = (
        frappe.qb.from_(Appointment)
        .select(
            Appointment.name,
            Appointment.status,
            Appointment.custom_subject.as_("subject"),
            Appointment.customer_details.as_("description"),
            Appointment.custom_color.as_("color"),
            Appointment.scheduled_time.as_("scheduled_time"),
            Appointment.custom_ends_on.as_("ends_on"),
            Appointment.owner,
            Appointment.custom_send_reminder.as_("send_reminder"),
			ConstantColumn(0).as_("all_day"),
        ).where(
			(
				functions.Date(Appointment.scheduled_time).between(start, end)
				| functions.Date(Appointment.custom_ends_on).between(start, end)
				| (
					(functions.Date(Appointment.scheduled_time) <= start)
					& (functions.Date(Appointment.custom_ends_on) >= end)
	   			  )
			)
			& (
				(Appointment.owner == user)
				| share_query
			)
		)
    )
	if for_reminder:
		query = query.where(
			Appointment.custom_send_reminder == 1
		)
	
	appointments = query.run(as_dict=True)
	return appointments

# Google Calendar
def insert_event_in_google_calendar(doc):
	"""
	Insert Events in Google Calendar if sync_with_google_calendar is checked.
	"""
	if (
		not doc.custom_sync_with_google_calendar
		or doc.custom_pulled_from_google_calendar
		or not frappe.db.exists("Google Calendar", {"name": doc.custom_google_calendar})
	):
		return

	google_calendar, account = get_google_calendar_object(doc.custom_google_calendar)

	if not account.push_to_google_calendar:
		return

	event = {"summary": doc.custom_subject, "description": doc.customer_details, "google_calendar_event": 1}
	event.update(
		format_date_according_to_google_calendar(
			0, get_datetime(doc.scheduled_time), get_datetime(doc.ends_on) if doc.ends_on else None
		)
	)

	event.update({"attendees": get_attendees(doc)})

	conference_data_version = 0

	try:
		event = (
			google_calendar.events()
			.insert(
				calendarId=doc.custom_google_calendar_id,
				body=event,
				conferenceDataVersion=conference_data_version,
				sendUpdates="all",
			)
			.execute()
		)

		frappe.db.set_value(
			"Event",
			doc.name,
			{"google_calendar_event_id": event.get("id"), "google_meet_link": event.get("hangoutLink")},
			update_modified=False,
		)

		frappe.msgprint(_("Event Synced with Google Calendar."))
	except HttpError as err:
		frappe.throw(
			_("Google Calendar - Could not insert event in Google Calendar {0}, error code {1}.").format(
				account.name, err.resp.status
			)
		)


def update_event_in_google_calendar(doc, method=None):
	"""
	Updates Events in Google Calendar if any existing event is modified in Frappe Calendar
	"""
	# Workaround to avoid triggering updating when Event is being inserted since
	# creation and modified are same when inserting doc
	if (
		not doc.custom_sync_with_google_calendar
		or doc.modified == doc.creation
		or not frappe.db.exists("Google Calendar", {"name": doc.custom_google_calendar})
	):
		return

	if doc.custom_sync_with_google_calendar and not doc.custom_google_calendar_event_id:
		# If sync_with_google_calendar is checked later, then insert the event rather than updating it.
		insert_event_in_google_calendar(doc)
		return

	google_calendar, account = get_google_calendar_object(doc.custom_google_calendar)

	if not account.push_to_google_calendar:
		return

	try:
		event = (
			google_calendar.events()
			.get(calendarId=doc.custom_google_calendar_id, eventId=doc.custom_google_calendar_event_id)
			.execute()
		)

		event["summary"] = doc.custom_subject
		event["description"] = doc.customer_details
		event["recurrence"] = []
		event["status"] = (
			"cancelled" if doc.status == "Cancelled" or doc.status == "Closed" else event.get("status")
		)
		event.update(
			format_date_according_to_google_calendar(
				0, get_datetime(doc.scheduled_time), get_datetime(doc.ends_on) if doc.ends_on else None
			)
		)

		conference_data_version = 0
		event.update({"attendees": get_attendees(doc)})
		event = (
			google_calendar.events()
			.update(
				calendarId=doc.custom_google_calendar_id,
				eventId=doc.custom_google_calendar_event_id,
				body=event,
				conferenceDataVersion=conference_data_version,
				sendUpdates="all",
			)
			.execute()
		)

		# if add_video_conferencing enabled or disabled during update, overwrite
		frappe.db.set_value(
			"Event",
			doc.name,
			{"google_meet_link": event.get("hangoutLink")},
			update_modified=False,
		)
		doc.notify_update()

		frappe.msgprint(_("Event Synced with Google Calendar."))
	except HttpError as err:
		frappe.throw(
			_("Google Calendar - Could not update Event {0} in Google Calendar, error code {1}.").format(
				doc.name, err.resp.status
			)
		)


def delete_event_from_google_calendar(doc, method=None):
	"""
	Delete Events from Google Calendar if Frappe Event is deleted.
	"""

	if not frappe.db.exists("Google Calendar", {"name": doc.custom_google_calendar, "push_to_google_calendar": 1}):
		return

	google_calendar, _ = get_google_calendar_object(doc.custom_google_calendar)

	try:
		event = (
			google_calendar.events()
			.get(calendarId=doc.custom_google_calendar_id, eventId=doc.custom_google_calendar_event_id)
			.execute()
		)
		event["recurrence"] = None
		event["status"] = "cancelled"

		google_calendar.events().update(
			calendarId=doc.custom_google_calendar_id, eventId=doc.custom_google_calendar_event_id, body=event
		).execute()
	except HttpError as err:
		frappe.msgprint(
			_("Google Calendar - Could not delete Event {0} from Google Calendar, error code {1}.").format(
				doc.name, err.resp.status
			)
		)

def get_attendees(doc):
	"""
	Returns a list of dicts with attendee emails, if available in event_participants table
	"""
	if not doc.customer_email:
		frappe.msgprint(
			_("Google Calendar - Contact / email not found. Did not add email for -<br>{0}").format(
				f"{doc.appointment_with} {doc.party}"
			),
			alert=True,
			indicator="yellow",
		)
	attendees = [doc.customer_email]

	return attendees
