from erpnext.stock.doctype.item.item import Item as BaseItem


class Item(BaseItem):
    def validate(self):
        super().validate()
        self.set_search_field()

    def set_search_field(self):
        search = []
        if isinstance(self.name, str):
            search.append(self.name)
        if isinstance(self.stock_uom, str):
            search.append(self.stock_uom)
        if isinstance(self.item_name, str):
            search.append(self.item_name)
        if isinstance(self.description, str):
            search.append(self.description)
        if isinstance(self.item_group, str):
            search.append(self.item_group)
        if isinstance(self.brand, str):
            search.append(self.brand)
        self.custom_search = " ".join(search)
