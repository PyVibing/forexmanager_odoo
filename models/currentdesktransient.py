from odoo import fields, models
from odoo.exceptions import ValidationError
import base64
from ..utils import notification


class CurrentDeskTransient(models.TransientModel):
    """A model for updating the current desk where user is working."""
    _name = "forexmanager.currentdesktransient"
    _description = "Vinculación de ventanilla"

    # MAIN FIELDS
    user_id = fields.Many2one("res.users", default=lambda self: self.env.uid, required=True, readonly=True, string="Usuario")
    current_desk = fields.Many2one(related="user_id.current_desk_id", string="Ventanilla actual", readonly=True)
    name = fields.Char(string="Nombre", default="Vinculación de ventanilla", readonly=True)
    desk_code = fields.Binary(string="Vincular ventanilla", required=True)


    def update_current_desk(self):
        for rec in self:
            if rec.desk_code:
                try:
                    content = base64.b64decode(self.desk_code)
                    code = content.decode("utf-8")
                except Exception as e:
                    raise ValidationError("Error al leer el contenido del archivo. Contacte con su administrador de sistemas.")
                
                desk = self.env["forexmanager.desk"].sudo().search([
                    ("desk_code", "=", code)
                    ], limit=1)
                if not desk:
                    raise ValidationError("Este código no está asociado a ninguna ventanilla. Contacte con su administrador de sistemas.")
                
                # Update current_desk_id in res.users
                user = self.env["res.users"].search([
                    ("id", "=", self.env.uid)
                    ])
                if rec.current_desk.id == desk.id:
                    notification(rec, "Ya estabas en esta ventanilla", 
                                 "Ya habías declarado esta misma ventanilla como tu ventanilla actual. " \
                                 "Solo debes hacer esto si cambias físicamente de lugar de trabajo.", "warning")
                else:
                    user.write({
                        "current_desk_id":  desk.id
                        })
                    notification(rec, f"Bienvenido a la ventanilla {desk.name} (ID: {desk.id})", 
                                "Has declarado que te encuentras en esta ventanilla. Si en algún momento cambias " \
                                "temporalmente de sitio de trabajo, recuerda actualizar esta información antes de iniciar sesión.",
                                "success", True)            
            else:
                rec.read_code = False
                