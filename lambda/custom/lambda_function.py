import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class NewSymptomIntentHandler(AbstractRequestHandler):
    """Handler for NewSymptomIntent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("NewSymptomIntent")(handler_input)

    async def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        print("DEBUG: NewSymptomIntentHandler started")
        attributes_manager = handler_input.attributes_manager
        session_attributes = attributes_manager.get_session_attributes()

        new_symptom_slot = ask_utils.request_util.get_slot(handler_input, 'newSymptom')
        new_symptom = new_symptom_slot.value if new_symptom_slot else None

        speak_output = ''
        reprompt_output = ''

        if new_symptom:
            speak_output = f"新しい症状は {new_symptom} ですね！お大事に！"
            reprompt_output = speak_output
        else:
            speak_output = '申し訳ありません、症状が聞き取れませんでした。もう一度お話しください。'
            reprompt_output = speak_output
        
        attributes_manager.set_session_attributes(session_attributes)

        print("DEBUG: Returning response from NewSymptomIntentHandler")
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt_output)
                .response
        )
 
class CustomExceptionHandler(AbstractExceptionHandler):
    """Handler for all other exceptions."""
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True
 
    async def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)
 
        speak_output = "申し訳ありません、スキルの処理中にエラーが発生しました。もう一度お試しください。"
 
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CustomExceptionHandler(AbstractExceptionHandler):
    """Handler for all other exceptions."""
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    async def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "申し訳ありません、スキルの処理中にエラーが発生しました。もう一度お試しください。"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


# リクエストハンドラーの登録
sb = SkillBuilder()

sb.add_request_handler(NewSymptomIntentHandler())
sb.add_exception_handler(CustomExceptionHandler())

lambda_handler = sb.lambda_handler()
