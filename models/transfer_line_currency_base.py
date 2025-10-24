from odoo import fields, api, models
from odoo.exceptions import ValidationError
from ..utils import notification


class TransferBase(models.AbstractModel):
    _name = "forexmanager.transfer.line.currency.base"
    _description = "Monedas a traspasar a cada ventanilla"

    # MAIN FIELDS
    currency_id = fields.Many2one("forexmanager.currency", string="Divisa", required=True)
    amount = fields.Float(string="Cantidad", required=True)
    
    # DELETE