from odoo import fields, models, api
from odoo.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from ..utils import notification


class Calculation(models.Model):
    """A model for calculating the conversion from source to destination currency."""
    _name = "forexmanager.calculation"
    _description = "Cálculo para cambio de divisas"

    MARGIN = 1.4 # Commercial margin over the base rate (official rate)

    # MAIN FIELDS
    currency_base_id = fields.Many2one("res.currency", default=125, readonly=True, required=True) # EUR by default
    name = fields.Char(compute="_compute_name", store=True, string="Nombre")
    date = fields.Datetime(related="operation_id.date", string="Fecha", store=True, readonly=True) 
    user_id = fields.Many2one("res.users", string="Empleado", default=lambda self: self.env.uid, readonly=True)
    currency_source_id = fields.Many2one("forexmanager.currency", string="Divisa ofrecida", required=True)
    currency_target_id = fields.Many2one("forexmanager.currency", string="Divisa solicitada", required=True)
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
        ("95", "95%"),
        ], string="Descuento", default="0", required=True)
    payment_type = fields.Selection([
        ("cash", "Efectivo"),
        ], string="Pago en", default="cash", required=True)
    delivery_type = fields.Selection([
        ("cash", "Efectivo")
        ], string="Entrega en", default="cash", required=True)
    base_rate = fields.Float(compute="_compute_rate", store=True, digits=(16, 6))
    buy_rate = fields.Float(compute="_compute_rate", store=True, digits=(16, 6))
    sell_rate = fields.Float(compute="_compute_rate", store=True, digits=(16, 6))
    worksession_id = fields.Many2one("forexmanager.worksession", related="operation_id.worksession_id", string="Sesión", store=True)

    # OTHER FIELDS
    # Relation with Operation
    operation_id = fields.Many2one("forexmanager.operation", copy=False)
    # To show the ID integer in the list view
    operation_ref = fields.Integer(related="operation_id.id", string="ID Op.", store=True, copy=False)
    # Images of admitted bills and coins (for source_currency)
    images_ids = fields.One2many("forexmanager.image", compute="_compute_images_ids", string="Libro de billetes")
    # Value pair under the original amount
    received_amount_under = fields.Float(default=0, readonly=True, store=False)
    delivered_amount_under = fields.Float(default=0, readonly=True, store=False)
    # Value pair over the original amount
    received_amount_over = fields.Float(default=0, readonly=True, store=False)
    delivered_amount_over = fields.Float(default=0, readonly=True, store=False)
    # These fields will take the value after clicking the button to select the right amount (under or over the original amount)
    # when original amount doesn't match the bills and coins breakdown. This will trigger the compute_method
    # for amount_received and amount_delivered
    new_received_value = fields.Float(default=0, readonly=True, store=False)
    new_delivered_value = fields.Float(default=0, readonly=True, store=False)
    # currency real (res.currency) for showing right symbol in the views for the monetary fields
    source_currency_real_id = fields.Many2one(related="currency_source_id.currency_id", readonly=True, store=False)
    target_currency_real_id = fields.Many2one(related="currency_target_id.currency_id", readonly=True, store=False)
    # Boolean buttons (to avoid auto-save when clicking a button)
    switch_button = fields.Boolean(default=False, store=False)
    bills_book = fields.Boolean(default=False, store=False)
    over_value_button = fields.Boolean(default=False, store=False)
    under_value_button = fields.Boolean(default=False, store=False)
    # Others
    up_down = fields.Char(store=False, readonly=True) # To know if user click on over_value or under_value
    available = fields.Boolean(default=True, store=False) # True if currency_balance > amount_delivered
    repeated_line = fields.Boolean(default=False, store=False) # To know if there is already a calculation line for these same currencies
     

    # Calculates if there is already a change line for these currencies in the same order.
    # EUR-USD and USD-EUR is allowed since currencies are the same but not same order.
    # Two EUR-USD lines, for example, are not allowed
    @api.onchange("source_currency_real_id", "target_currency_real_id")
    def _onchange_currencies_id(self):
        for rec in self:
            if (rec.source_currency_real_id and rec.target_currency_real_id):
                other_lines = [i for i in rec.operation_id.calculation_ids if i != rec]
                
                for i in other_lines:
                    rec.repeated_line = False # Restart value from previous True
                    if (i.source_currency_real_id == rec.source_currency_real_id) and (
                        i.target_currency_real_id == rec.target_currency_real_id):
                        rec.repeated_line = True
                        notification(rec, "Ya existe un movimiento similar", 
                                    f"Ya existe la línea de cambio {rec.source_currency_real_id.name} a {rec.target_currency_real_id.name}. \
                                    No puedes agregarla nuevamente. Si prefieres, modifica las cantidades de la línea que ya está creada.",
                                    "warning")
                        break

    @api.depends("currency_source_id.unit_ids.image_ids")
    def _compute_images_ids(self):
        for rec in self:
            rec.images_ids = rec.currency_source_id.unit_ids.mapped("image_ids")
    
    def check_availability(self, currency_id, amount):
        for rec in self:
            # Check (from opening_desk_id balance, even if user is in a secondary desk) 
            # if there is enough currency to deliver to client
            cashcount = rec.env["forexmanager.cashcount"].search([
                ("currency_id", "=", currency_id),
                ("desk_id", "=", rec.operation_id.worksession_id.opening_desk_id)
                ], limit=1)
            rec.available = cashcount.balance >= amount if cashcount else False
            return rec.available
    
    # Auxiliar method called from aux_calc_amount_received() and aux_calc_amount_delivered()
    def recalculate_amount(self, currency_id, amount, up_down):
        # Recalculate having in consideration accepted bills and coins (in breakdown model)
        amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        breakdown_recs = self.env["forexmanager.breakdown"].search([
            ("currency_real_id", "=", currency_id)
        ])
        bills = [Decimal(str(i.value)) for i in breakdown_recs if i.value > 0] if breakdown_recs else []
        coins = [Decimal(str(i.value)) for i in breakdown_recs if i.value > 0] if breakdown_recs else []
        if not bills and not coins:
            raise ValidationError("No existe desglose de billetes ni monedas admitidos para una de las monedas seleccionadas. Consulte con su administrador de sistemas.")
        values = bills + coins

        remainders = []
        for value in values:
            remainder = (amount % value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if remainder == 0:
                return float(amount), False
            else:
                if up_down == "down":
                    remainders.append(remainder)
                elif up_down == "up":
                    remainders.append(value - remainder)
                else:
                    raise ValidationError("Parámetro incorrecto. No se pudo completar el cálculo. " \
                                            "Contacte con su equipo técnico para solucionarlo.")
        
        if up_down == "down":
            new_amount = amount - min(remainders)
        else:  # if "up"
            new_amount = amount + min(remainders)
        
        return float(new_amount), True

    
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
                    
                return round(amount_received, 2), round(amount_delivered, 2)
            
            if rec.up_down: # If has a value, means the user already click on the upper or under value of original amount
                amount_received, amount_delivered = calculate(rec.up_down)
            else:
                amount_received, amount_delivered = calculate("down") # By default

            # Let's give an over_value and under_value of the initial amounts, depending in bills and coins accepted
            # for both currencies
            if (rec.amount_delivered > 0 and rec.amount_delivered != amount_delivered):
                amount_received, amount_delivered = calculate("up") # Let's check now "up"
                if (rec.amount_delivered > 0 and rec.amount_delivered != amount_delivered):
                    # Pair 1 (under)
                    rec.received_amount_under, rec.delivered_amount_under = calculate("down")
                    # Pair 2 (over)
                    rec.received_amount_over, rec.delivered_amount_over = calculate("up")
                else:
                    rec.amount_received, rec.amount_delivered = amount_received, amount_delivered
                    if not rec.check_availability(rec.currency_target_id, rec.amount_delivered):
                        notification(rec, "No hay suficiente balance", "No existe suficiente balance de la divisa solicitada", "warning")
            else:
                rec.amount_received, rec.amount_delivered = amount_received, amount_delivered
                if not rec.check_availability(rec.currency_target_id, rec.amount_delivered):
                    notification(rec, "No hay suficiente balance", "No existe suficiente balance de la divisa solicitada", "warning")
                         
    
    @api.depends("amount_delivered", "target_currency_real_id", "buy_rate", "sell_rate", "new_delivered_value")
    def _compute_amount_received(self):
        for rec in self:
            if not rec.currency_source_id or not rec.currency_target_id or rec.amount_delivered < 0:
                rec.amount_received = False
                rec.amount_delivered = False

            if rec.new_received_value or rec.new_delivered_value:
                rec.amount_received = rec.new_received_value  
                rec.amount_delivered = rec.new_delivered_value

                if not rec.check_availability(rec.currency_target_id, rec.amount_delivered):
                    notification(rec, "No hay suficiente balance", "No existe suficiente balance de la divisa solicitada", "warning")

                # Restart values
                rec.new_received_value = 0
                rec.new_delivered_value = 0
                rec.received_amount_under = 0
                rec.received_amount_over = 0
                rec.delivered_amount_under = 0
                rec.delivered_amount_over = 0
                rec.over_value_button = False
                rec.under_value_button = False              
            else:
                # if rec.up_down has a value, means amounts were recalculated, so it's not recalculated again
                if rec.amount_delivered and not rec.up_down: 
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
            
            if rec.up_down: # If has a value, means the user already click on the upper or under value of original amount
                amount_received, amount_delivered = calculate(rec.up_down)
            else:
                amount_received, amount_delivered = calculate("down") # By default

            # Let's give an over_value and under_value of the initial amounts, depending in bills and coins accepted
            # for both currencies
            if (rec.amount_received > 0 and rec.amount_received != amount_received):         
                # Pair 1 (under)
                rec.received_amount_under, rec.delivered_amount_under = calculate("down")
                # Pair 2 (over)
                rec.received_amount_over, rec.delivered_amount_over = calculate("up")
            else:
                rec.amount_received, rec.amount_delivered = amount_received, amount_delivered

                if not rec.check_availability(rec.currency_target_id, rec.amount_delivered):
                    notification(rec, "No hay suficiente balance", "No existe suficiente balance de la divisa solicitada", "warning")       
            
    @api.depends("amount_received", "source_currency_real_id", "buy_rate", "sell_rate", "new_received_value")
    def _compute_amount_delivered(self):
        for rec in self:
            if not rec.currency_source_id or not rec.currency_target_id or rec.amount_received <= 0:
                rec.amount_received = False
                rec.amount_delivered = False

            
            if rec.new_received_value or rec.new_delivered_value:
                rec.amount_received = rec.new_received_value  
                rec.amount_delivered = rec.new_delivered_value

                if not rec.check_availability(rec.currency_target_id, rec.amount_delivered):
                    notification(rec, "No hay suficiente balance", "No existe suficiente balance de la divisa solicitada", "warning")

                # Restart values
                rec.new_received_value = 0
                rec.new_delivered_value = 0
                rec.received_amount_under = 0
                rec.received_amount_over = 0
                rec.delivered_amount_under = 0
                rec.delivered_amount_over = 0
                rec.over_value_button = False
                rec.under_value_button = False
            else: 
                # if rec.up_down has a value, means amounts were recalculated, so it's not recalculated again
                if rec.amount_received and not rec.up_down: 
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
                                    Si se trata de un doble cambio, agregue las dos líneas de cambio por separado.""", 
                                 "warning", sticky=True)
    
    # ------------- METHODS CALLED FROM CHECKBOXS ------------- #    
    @api.onchange("switch_button")
    def reverse_fields(self):
        for rec in self:
            if rec.switch_button:        
                if rec.currency_source_id and rec.currency_target_id:
                    temp = rec.currency_source_id
                    rec.currency_source_id = rec.currency_target_id
                    rec.currency_target_id = temp            
                elif rec.currency_source_id and not rec.currency_target_id:
                    temp = rec.currency_source_id
                    rec.currency_source_id = False
                    rec.currency_target_id = temp            
                elif rec.currency_target_id and not rec.currency_source_id:
                    temp = rec.currency_target_id
                    rec.currency_target_id = False
                    rec.currency_source_id = temp
                rec.switch_button = False
    
    @api.onchange("under_value_button")
    def get_under_values(self):
        for rec in self:
            if rec.under_value_button:
                rec.up_down = "down"
                rec.new_received_value = rec.received_amount_under
                rec.new_delivered_value = rec.delivered_amount_under
    
    @api.onchange("over_value_button")
    def get_over_values(self):
        for rec in self:
            if rec.over_value_button:
                rec.up_down = "up"
                rec.new_received_value = rec.received_amount_over
                rec.new_delivered_value = rec.delivered_amount_over
