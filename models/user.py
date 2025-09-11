from odoo import fields, models


class Users(models.Model):
    _inherit = "res.users"
    _description = "A model for defyning users and related information about them."

    opening_desk_id = fields.Many2one("forexmanager.desk")