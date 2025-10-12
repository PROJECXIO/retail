frappe.ui.form.on("Customer", {
    async onload(frm){
        const pets = await frappe.db.get_list("Pet", { filters: {"customer": frm.doc.name}, fields: ["*"] }) || [];
        console.log(pets);
        const pets_profile = pets.map(pet => {
            let color = "red";
            if(pet.last_vaccine_exp_date){
                var date1 = new Date(pet.last_vaccine_exp_date);
                var date2 = new Date();
                var diffTime = date1.getTime() - date2.getTime();
                var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
                if(diffDays > 7){
                    color = "green";
                }
            }
            return `
            <a class="pet-card ${color}" href="/app/pet/${pet.name}" target="_blank">
                <img src="${pet.pet_image || '/assets/retail/images/logo.jpeg'}" alt="Pet Avatar" class="pet-avatar">
                <div class="pet-info">
                <h3 class="pet-name">${pet.pet_name}</h3>
                <p class="pet-type">${__("Type")}: ${pet.pet_type}</p>
                <p class="pet-dob">${__("Date of Birth")}: ${pet.date_of_birth || 'N/A'}</p>
                <p class="pet-vaccine">${__("Vaccine Expire")}: <span class="${color}">${pet.last_vaccine_exp_date }</span></p>
                </div>
            </a>`}).join("");
        $(frm.fields_dict['custom_customer_pets_profile'].wrapper).html(`
            <div class="pet-list">${pets_profile}</div>
            `)
        
    },
    custom_add_new_pet: function(frm){
        frappe.new_doc("Pet", {"customer": frm.doc.name});
    },
});
