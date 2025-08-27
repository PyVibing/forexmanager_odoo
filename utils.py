import requests
from odoo.exceptions import UserError

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
            "sticky": False
            },
        ) 