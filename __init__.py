from . import models

def initial_config(env):
    def activate_currencies(env):
        try:
            currencies = env['res.currency'].with_context(active_test=False).search([])
            if currencies:
                for i in currencies:
                    i.active = True
            print("Currencies activated")
        except Exception as e:
            print("Exception in init hook (file: __init__.py) - initial_config() --> activate_currencies:", e)
    
    activate_currencies(env)
    


    
