class LangGraphApp():
    """All workflows loaded into this class to be utilized where ever"""
    def init_app(self):
        # ---------------------- Load All Graph States ---------------------- #
        from app.graphs.agents.agent_jball_workflow import jball_agent_wf


        # ---------------------- Initialize entire lang graph app ---------------------- #
        self.__class__.jball_agent_wf = jball_agent_wf

    jball_agent_wf = None
