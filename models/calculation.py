from odoo import fields, models, api
from odoo.exceptions import ValidationError
from decimal import Decimal, ROUND_DOWN
from ..utils import notification


class Calculation(models.Model):
    _name = "forexmanager.calculation"
    _description = "A model for calculating from source to destination currency."

    MARGIN = 1.4 # Commercial margin over the base rate (official rate)
    currency_base_id = fields.Many2one("res.currency", default=125, readonly=True, required=True) # EUR by default

    name = fields.Char(compute="_compute_name", store=True, string="Nombre")
    date = fields.Date(string="Fecha", readonly=True, copy=False) # compute datetime.now().date() and readonly True
    user_id = fields.Many2one("res.users", string="Empleado", default=lambda self: self.env.uid, readonly=True, copy=False)
    # Relation with Operation
    operation_id = fields.Many2one("forexmanager.operation")
    operation_ref = fields.Integer(related="operation_id.id", string="ID Op.", store=True)    
    # Currency and amount
    currency_source_id = fields.Many2one("forexmanager.currency", string="Moneda ofrecida", required=True)
    currency_target_id = fields.Many2one("forexmanager.currency", string="Moneda solicitada", required=True)
    amount_received = fields.Monetary(
        string="Cantidad recibida",
        currency_field="source_currency_real_id",
        compute="_compute_amount_received",
        inverse="_inverse_amount_received",
        store=True,
        )
    amount_delivered = fields.Monetary(
        string="Cantidad entregada",
        currency_field="target_currency_real_id",
        compute="_compute_amount_delivered",
        inverse="_inverse_amount_delivered",
        store=True,
        )
    discount = fields.Selection([
        ("0", "0%"),
        ("5", "5%"),
        ("10", "10%"),
        ("15", "15%"),
        ("20", "20%"),
        ("25", "25%"),
        ("30", "30%"),
        ("35", "35%"),
        ("40", "40%"),
        ("45", "45%"),
        ("50", "50%"),
        ("55", "55%"),
        ("60", "60%"),
        ("65", "65%"),
        ("70", "70%"),
        ("75", "75%"),
        ("80", "80%"),
        ("85", "85%"),
        ("90", "90%"),
        ], string="Descuento", default="0", required=True)
    payment_type = fields.Selection([
        ("cash", "Efectivo"),
        ("card", "Tarjeta")
        ], string="Método de pago", default="cash", required=True)
    delivery_type = fields.Selection([
        ("cash", "Efectivo")
        ], string="Método de entrega", default="cash", required=True)
    base_rate = fields.Float(compute="_compute_rate", store=True)
    buy_rate = fields.Float(compute="_compute_rate", store=True)
    sell_rate = fields.Float(compute="_compute_rate", store=True)

    # Technical fields - currency real (res.currency) for showing right symbol in the views for the monetary fields
    source_currency_real_id = fields.Many2one(related="currency_source_id.currency_id", readonly=True)
    target_currency_real_id = fields.Many2one(related="currency_target_id.currency_id", readonly=True)

    def recalculate_amount(self, currency_id, amount, up_down):
        # Recalculate having in consideration accepted bills and coins (in breakdown model)
        for rec in self:
            breakdown_recs = self.env["forexmanager.breakdown"].search([
                ("currency_real_id", "=",currency_id)
                ])
            bills = [i.bill_value for i in breakdown_recs if i.bill_value>0] if breakdown_recs else []
            coins = [i.coin_value for i in breakdown_recs if i.coin_value>0] if breakdown_recs else []
            if not bills and not coins:
                raise ValidationError("No existe desglose de billetes ni monedas admitidos para una de las monedas seleccionadas.")
            
            values = bills + coins
            to_substract = []

            for value in values:
                remainder = amount % value
                if remainder == 0:
                    return amount, False
                else:
                    if up_down == "down":
                        to_substract.append(remainder)
                    elif up_down == "up":
                        to_substract.append(value - remainder)
                    else:
                        raise ValidationError("Parámetro incorrecto. No se pudo completar el cálculo. Contacte con su equipo técnico para solucionarlo.")
            
            if up_down == "down":
                new_amount = amount - min(to_substract)
            else: # if 'up'
                new_amount = amount + min(to_substract)

            if min(to_substract) < 0.02:
                    return new_amount, False # Omit a very small difference to avoid looping forever in currencies with no small coins
            return new_amount, True
    
    def aux_calc_amount_received(self):
        for rec in self:
            def calculate(up_down):
                # Recalculate amount_delivered and adjust it depending on the accepted bills and coins
                amount_delivered, recalculated_delivered = rec.recalculate_amount(rec.target_currency_real_id, rec.amount_delivered, up_down)
                
                # Calculate amount_received from amount_delivered
                if rec.target_currency_real_id == rec.currency_base_id: # If clients buys base_currency
                    amount_received = amount_delivered * rec.sell_rate
                else: # If clients offers base_currency                    
                    amount_received = amount_delivered / rec.buy_rate               
                
                # Recalculate amount_received and adjust it depending on the accepted bills and coins
                amount_received, recalculated_received = rec.recalculate_amount(rec.source_currency_real_id, amount_received, up_down)

                while recalculated_received: # while amount_delivered is recalculated and readjusted
                    # Calculate amount_delivered back from recalculated amount_received
                    if rec.source_currency_real_id == rec.currency_base_id: # If clients offers base_currency
                        amount_delivered = amount_received * rec.buy_rate
                    else: # If clients buys base_currency
                        amount_delivered = amount_received / rec.sell_rate

                    # Recalculate amount_delivered and adjust it depending on the accepted bills and coins
                    amount_delivered, recalculated_delivered = rec.recalculate_amount(
                        rec.target_currency_real_id, amount_delivered, up_down
                        )
                    if not recalculated_delivered: # After recalculating the amount_received, if amount_delivered did not changed, break
                        break
                    
                    # Calculate amount_received back from recalculated amount_delivered
                    if rec.target_currency_real_id == rec.currency_base_id: # If clients buys base_currency
                        amount_received = amount_delivered * rec.sell_rate
                    else: # If clients offers base_currency                    
                        amount_received = amount_delivered / rec.buy_rate               
                    
                    # Recalculate amount_received and adjust it depending of the accepted bills and coins
                    amount_received, recalculated_received = rec.recalculate_amount(
                        rec.source_currency_real_id, amount_received, up_down
                        )
                    
                return amount_received, amount_delivered

            rec.amount_received, rec.amount_delivered = calculate("down")
                         
    
    @api.depends("amount_delivered", "target_currency_real_id", "buy_rate", "sell_rate")
    def _compute_amount_received(self):
        for rec in self:
            if rec.amount_delivered and rec.target_currency_real_id:
                rec.aux_calc_amount_received()                

    def aux_calc_amount_delivered(self):
        for rec in self:
            def calculate(up_down):
                # Recalculate amount_received and adjust it depending on the accepted bills and coins
                amount_received, recalculated_received = rec.recalculate_amount(rec.source_currency_real_id, rec.amount_received, up_down)

                # Calculate amount_delivered from amount_received
                if rec.source_currency_real_id == rec.currency_base_id: # If clients offers base_currency
                    amount_delivered = amount_received * rec.buy_rate
                else: # If clients buys base_currency
                    amount_delivered = amount_received / rec.sell_rate

                # Recalculate amount_delivered and adjust it depending on the accepted bills and coins
                amount_delivered, recalculated_delivered = rec.recalculate_amount(rec.target_currency_real_id, amount_delivered, up_down)

                while recalculated_delivered: # while amount_delivered is recalculated and readjusted
                    # Calculate amount_received back from recalculated amount_delivered
                    if rec.target_currency_real_id == rec.currency_base_id: # If clients buys base_currency
                        amount_received = amount_delivered * rec.sell_rate
                    else: # If clients offers base_currency                    
                        amount_received = amount_delivered / rec.buy_rate

                    # Recalculate amount_received and adjust it depending on the accepted bills and coins
                    amount_received, recalculated_received = rec.recalculate_amount(
                        rec.source_currency_real_id, amount_received, up_down
                        )                    
                    if not recalculated_received: # After recalculating the amount_delivered, if amount_received did not changed, break
                        break
                    
                    # Calculate amount_delivered back from recalculated amount_received
                    if rec.source_currency_real_id == rec.currency_base_id:
                        amount_delivered = amount_received * rec.buy_rate
                    else:
                        amount_delivered = amount_received / rec.sell_rate

                    # Recalculate amount_delivered and adjust it depending of the accepted bills and coins
                    amount_delivered, recalculated_delivered = rec.recalculate_amount(
                        rec.target_currency_real_id, amount_delivered, up_down
                        )
                    
                return amount_received, amount_delivered
        
            rec.amount_received, rec.amount_delivered = calculate("down")

    @api.depends("amount_received", "source_currency_real_id", "buy_rate", "sell_rate")
    def _compute_amount_delivered(self):
        for rec in self:
            if rec.amount_received:
                rec.aux_calc_amount_delivered()                                  
    
    # --- Inverse ---
    def _inverse_amount_received(self):
        # If field amount_received changes, here we will recalculate amount_delivered.
        for rec in self:
            rec._compute_amount_delivered()

    def _inverse_amount_delivered(self):
        # If field amount_delivered changes, here we will recalculate amount_received.
        for rec in self:
            rec._compute_amount_received()

    @api.depends("source_currency_real_id", "target_currency_real_id", "amount_received", "amount_delivered", "payment_type", "delivery_type")
    def _compute_name(self):
        for rec in self:
            if rec.amount_received and rec.source_currency_real_id and rec.amount_delivered and rec.target_currency_real_id:
                rec.name = f"{rec.amount_received} {rec.source_currency_real_id.name} ({rec.payment_type}) a {rec.amount_delivered} {rec.target_currency_real_id.name} ({rec.delivery_type})"
            else:
                rec.name = "Cálculo de cambio de moneda"
    
    @api.depends("source_currency_real_id", "target_currency_real_id", "discount")
    def _compute_rate(self):
        for rec in self:
            if rec.source_currency_real_id and rec.target_currency_real_id:
                # If both currencies are the same
                if rec.source_currency_real_id == rec.target_currency_real_id:
                    rec.base_rate = False
                    rec.buy_rate = False
                    rec.sell_rate = False
                    notification(rec, "Ambas monedas no pueden ser la misma", 
                                 "La moneda ofrecida y demandada no pueden ser iguales.",
                                 "warning")
                # If currency_base is one of the two values, means is a single change
                elif rec.source_currency_real_id == rec.currency_base_id or rec.target_currency_real_id == rec.currency_base_id:
                    if rec.source_currency_real_id != rec.currency_base_id:
                        currency = self.env["forexmanager.currency"].search([
                                ("currency_id", "=", rec.source_currency_real_id)
                                ], limit=1)
                        
                    elif rec.target_currency_real_id != rec.currency_base_id:
                        currency = self.env["forexmanager.currency"].search([
                                ("currency_id", "=", rec.target_currency_real_id)
                                ], limit=1)
                    
                    rec.base_rate = currency.base_rate
                        
                    sell_no_discount_rate = rec.base_rate * rec.MARGIN
                    sell_difference = sell_no_discount_rate - currency.base_rate
                    sell_add_to_base = sell_difference * ((100 - int(rec.discount)) / 100) # Discount is applied to difference between base and commercial rate
                    rec.sell_rate = rec.base_rate + sell_add_to_base                    

                    buy_no_discount_rate = rec.base_rate / rec.MARGIN
                    buy_difference = currency.base_rate - buy_no_discount_rate
                    buy_substract_from_base = buy_difference * ((100 - int(rec.discount)) / 100) # Discount is applied to difference between base and commercial rate
                    rec.buy_rate = rec.base_rate - buy_substract_from_base
                # If currency_base is NOT one of the two values, means is a double change (not allowed, must be done in 2 parts)
                else:
                    rec.base_rate = False
                    rec.buy_rate = False
                    rec.sell_rate = False
                    notification(rec, f"Debe incluir {rec.currency_base_id.name}", 
                                 f"""Las dos monedas no pueden ser distintas a {rec.currency_base_id.name}. 
                                    Si se trata de un doble cambio, agruegue las dos líneas de cambio por separado.""", 
                                 "warning")
    
    def reverse_fields(self):
        for rec in self:
            if rec.amount_received and rec.amount_delivered and rec.currency_source_id and rec.currency_target_id:
                to_source_amount = rec.amount_delivered
                to_source_currency = rec.currency_target_id
                to_target_currency = rec.currency_source_id

                rec.amount_delivered = False # So its calculated from the amount_received amount
                rec.currency_target_id = False
                rec.currency_source_id = False

                rec.currency_target_id = to_target_currency
                rec.currency_source_id = to_source_currency
                rec.amount_received = to_source_amount
                
            elif rec.currency_source_id and rec.currency_target_id:
                temp = rec.currency_source_id
                rec.currency_source_id = rec.currency_target_id
                rec.currency_target_id = temp
            
