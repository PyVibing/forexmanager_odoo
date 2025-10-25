from odoo import fields, models


class Users(models.Model):
    """A model for defyning users and related information about them."""
    
    _inherit = "res.users"
    _description = "Usuario"

    # ADDED FIELDS TO RES.USERS
    current_desk_id = fields.Many2one("forexmanager.desk")
    opening_desk_id = fields.Many2one("forexmanager.desk")