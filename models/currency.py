from odoo import fields, models, api
from odoo.exceptions import ValidationError
from ..utils import get_base_rate, notification, create_initial_inventories


class Currency(models.Model):
    """A model for defining the allowed currencies for this exchange company, and balance."""

    _name = "forexmanager.currency"
    _description = "Divisas"

    # MAIN FIELDS
    currency_base_id = fields.Many2one("res.currency", default=125, readonly=True, required=True) # EUR by default
    name = fields.Char(default="Nueva divisa", compute="_compute_name", store=True, required=True, string="Nombre completo")
    currency_id = fields.Many2one("res.currency", string="ID original", required=True,)
    initials = fields.Char(related="currency_id.name", readonly=True, store=True, string="Iniciales")
    symbol = fields.Char(related="currency_id.symbol", readonly=True, store=True, string="Símbolo")
    short_name = fields.Char(related="currency_id.full_name", readonly=True, store=True, string="Nombre")
    base_rate = fields.Float(compute="_compute_base_rate") # currency_id related to currency_base_id

    # OTHER FIELDS
    # Units_ids is mandatory in create() and write()
    unit_ids = fields.One2many("forexmanager.breakdown", "currency_id", string="Billetes y monedas aceptadas") # Bill and coins
    workcenter_ids = fields.Many2many(
        comodel_name="forexmanager.workcenter",
        relation="workcenter_currency_rel",
        column1="currency_id",
        column2="workcenter_id",
        string="Centros que usan esta moneda"
        )

    @api.depends("currency_id")
    def _compute_name(self):
        for rec in self:
            if rec.currency_id:
                rec.name = f"{rec.currency_id.name}  ({rec.currency_id.full_name})"
            else:
                rec.name = "Nueva divisa"
    
    @api.depends("currency_id")
    def _compute_base_rate(self):
        # Some currencies are not suported by the current api
        for rec in self:
            if rec.currency_id:
                if rec.currency_id != rec.currency_base_id:
                    rec.base_rate = get_base_rate(from_currency=rec.currency_base_id.name, to_currency=rec.currency_id.name)
                else:
                    rec.base_rate = 1
            else:
                rec.base_rate = 0

    def create(self, vals):
        currency = super().create(vals)
        if not currency.unit_ids:
            raise ValidationError("Debes crear un desglose de monedas y billetes para esta divisa.")
        if not currency.workcenter_ids:
            notification(self, "Asignar centro de trabajo", 
                    "Recuerda luego asignar al menos un centro de trabajo a esta divisa. Ve a CONFIGURACIÓN/ADMINISTRAR CENTROS DE TRABAJO", 
                    "warning")

        # Add the new currency to every desk cashcount (inventory) for every desk in workcenter_ids
        desk_ids = currency.workcenter_ids.desk_ids
        if desk_ids:
            for desk_id in desk_ids:
                self.env["forexmanager.cashcount"].create({
                    "workcenter_id": desk_id.workcenter_id.id,
                    "desk_id": desk_id.id,
                    "currency_id": currency.id,
                    "balance": 0,
                    })            
        return currency

    def write(self, vals):
        for rec in self:
            if "workcenter_ids" in vals: # Means user is editing this field
                wc_vals = vals["workcenter_ids"]
                for wc in wc_vals:
                    wc_id = wc[1]
                    if wc[0] == 3: 
                        # Means the user is deleting the relation with this workcenter (wc_id)
                        # So let's check if there is balance > 0 for this currency in cashcount for every desk in 
                        # this workcenter and avoid deleting the relation
                        for desk_id in rec.workcenter_ids.desk_ids:
                            cashcount_rec = self.env["forexmanager.cashcount"].search([
                                ("desk_id", "=", desk_id),
                                ("workcenter_id", "=", wc_id),
                                ("currency_id", "=", rec.id)
                                ], limit=1)
                            if cashcount_rec:
                                if cashcount_rec.balance > 0:
                                    currency = cashcount_rec.currency_id
                                    raise ValidationError(f"No puedes desvincular este centro de trabajo de la divisa {currency.name} mientras existan ventanillas con saldo de esta divisa mayor que 0.00 {currency.initials}")
                                else:
                                    cashcount_rec.unlink()
                    elif wc[0] == 4:
                        # Means the user is adding this currency to a new workcenter
                        # So let's create the initial inventory (cashcount) for this currency and desk
                        currency = super().write(vals)
                        create_initial_inventories(rec.workcenter_ids)
            
            currency = super().write(vals)
            
            if not rec.unit_ids:
                raise ValidationError("Debes crear un desglose de monedas y billetes para esta divisa.")
                   
        return currency

    
    def unlink(self):
        for rec in self:
            # DELETE breakdown for this currency
            breakdown = self.env["forexmanager.breakdown"].search([
                ("currency_real_id", "=", rec.currency_id.id)
                ])
            if breakdown:
                breakdown.unlink()

            currency = super().unlink()
        return currency
    