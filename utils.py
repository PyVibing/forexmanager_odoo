import requests
from odoo.exceptions import UserError, ValidationError
        

def get_base_rate(from_currency, to_currency):
    URL = f"https://api.frankfurter.dev/v1/latest?base={from_currency}&symbols={to_currency}"
    
    try:
        rate = requests.get(URL).json()["rates"][to_currency]
    except requests.exceptions.RequestException as e:
        raise UserError(f"Error al intentar convertir la cantidad a la moneda seleccionada. No se pudo obtener el tipo de cambio: {e}")
    except KeyError:
        raise UserError("Error al intentar convertir la cantidad a la moneda seleccionada. Moneda no soportada para esta API.")
    
    return rate

def notification(self, title, body, message_type, sticky=False):
    self.env["bus.bus"]._sendone(
        self.env.user.partner_id,
        "simple_notification",
            {
            "type": f"{message_type}",
            "title": f"{title}",
            "message": f"{body}",
            "sticky": sticky
            },
        ) 

def create_initial_inventories(self):
    if not self.desk_ids:
        raise ValidationError("No hay ventanillas asociadas a este centro. Agregue al menos una ventanilla.")
    for desk_id in self.desk_ids:
        # Get new coins created after the desk creation (so we create the initial inventory - cashcount model)
        currencies_id = desk_id.workcenter_id.currency_ids # Look for currencies accepted in this workcenter
        if not currencies_id:
            raise ValidationError("No hay divisas asociadas a este centro de trabajo. Agregue al menos una divisa.")
        # Check if cashcount exists for every of these currencies
        for currency_id in currencies_id:
            cashcount = self.env["forexmanager.cashcount"].search([
                ("desk_id", "=", desk_id),
                ("currency_id", "=", currency_id)
                ])
            
            if not cashcount: # Let's create the initial inventory
                self.env["forexmanager.cashcount"].create({
                    "workcenter_id": desk_id.workcenter_id.id,
                    "desk_id": desk_id.id,
                    "currency_id": currency_id.id,
                    "balance": 0,
                    })