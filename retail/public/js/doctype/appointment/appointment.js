frappe.ui.form.on("Appointment", {
    refresh(frm){
        frm.trigger("set_label");
        frm.set_query("pet", "custom_appointment_services", function(doc){
            return {
                filters :{
                    customer: doc.party,
                }
            }
        })
    },
    appointment_with(frm){
        frm.trigger("set_label");
        frm.set_value("party", "");
    },
    async party(frm){
        if(!frm.doc.appointment_with || !frm.doc.party){
            await frm.set_value("customer_name", "");
            await frm.set_value("customer_phone_number", "");
            await frm.set_value("customer_email", "");
        }else{
            if(frm.doc.appointment_with == "Customer"){
                let mobile_no = await frappe.db.get_value("Customer", frm.doc.party, "mobile_no");
                mobile_no = mobile_no && mobile_no.message && mobile_no.message.mobile_no;
                let customer_name = await frappe.db.get_value("Customer", frm.doc.party, "customer_name");
                customer_name = customer_name && customer_name.message && customer_name.message.customer_name;
                await frm.set_value("customer_name", customer_name);
                await frm.set_value("customer_phone_number", mobile_no);
            }
        }
    },
    set_label(frm){
        frm.set_df_property("party", "label", __(frm.doc.appointment_with) || __("Party"));
        frm.set_df_property("customer_name", "label", __(`${frm.doc.appointment_with} Name`) || __("Party Name"));
    }
});
