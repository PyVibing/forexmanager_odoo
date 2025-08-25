{
    "name": "ForexManager: Cambio de divisas",
    "version": "1.0",
    "category": "Currency exchange",
    "summary": "Gestión para empresas orientadas al cambio de divisas ",
    "author": "Jeffry Hernández",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/calculation_views.xml",
        "views/operation_views.xml",
        "views/currency_views.xml",
        "views/menu_views.xml",
    ],
    "post_init_hook": "initial_config",
    "installable": True,
    "application": True,
}