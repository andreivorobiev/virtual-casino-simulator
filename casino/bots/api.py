# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.bots import profiles, controller, practice_opponents


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/bots")
    # Define the list_bots function used by this module.
    def list_bots(body, query):
        # Return the computed value to the caller.
        return {"bots": profiles.list_bots(), "capabilities": profiles.capabilities(), "practice_opponents": practice_opponents.list_accounts()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/bots/capabilities")
    # Define the capabilities function used by this module.
    def capabilities(body, query):
        # Return the computed value to the caller.
        return {"capabilities": profiles.capabilities()}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/bots/(?P<bot_id>[^/]+)")
    # Define the update_bot function used by this module.
    def update_bot(body, query, bot_id):
        # Return the computed value to the caller.
        return {"bot": profiles.update_bot(bot_id, body)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/bots/(?P<bot_id>[^/]+)/enable")
    # Define the enable_bot function used by this module.
    def enable_bot(body, query, bot_id):
        # Return the computed value to the caller.
        return {"bot": profiles.update_bot(bot_id, {"enabled": True})}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/bots/(?P<bot_id>[^/]+)/disable")
    # Define the disable_bot function used by this module.
    def disable_bot(body, query, bot_id):
        # Return the computed value to the caller.
        return {"bot": profiles.update_bot(bot_id, {"enabled": False})}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/bots/(?P<bot_id>[^/]+)/strategy")
    # Define the set_strategy function used by this module.
    def set_strategy(body, query, bot_id):
        # Return the computed value to the caller.
        return {"bot": profiles.update_bot(bot_id, {"strategies": {body.get("game_id"): body.get("strategy_id")}, "stakes": {body.get("game_id"): body.get("stake", 5)}})}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/(?P<game_id>[^/]+)/eligible-bots")
    # Define the eligible function used by this module.
    def eligible(body, query, game_id):
        # Return the computed value to the caller.
        return {"game_id": game_id, "bots": profiles.eligible_bots(game_id), "capabilities": profiles.capabilities().get(game_id, {"supports_bots": False, "strategies": []})}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/(?P<game_id>[^/]+)/bots/play-round")
    # Define the play function used by this module.
    def play(body, query, game_id):
        # Return the computed value to the caller.
        return controller.play_round(game_id)
