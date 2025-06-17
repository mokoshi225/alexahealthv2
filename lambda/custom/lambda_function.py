import logging
import os
import boto3
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
from datetime import date

# DynamoDB永続化アダプターの設定
ddb_region = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
ddb_table_name = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')

ddb_resource = boto3.resource('dynamodb', region_name=ddb_region)
dynamodb_adapter = DynamoDbAdapter(table_name=ddb_table_name, create_table=False, dynamodb_resource=ddb_resource)



logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

symptoms = ['発熱', 'めまい', '倦怠感', '吐き気', '頭痛', '咳', '鼻水', '喉の痛み', '関節痛', '筋肉痛', '食欲不振', '下痢', '便秘', '不眠']

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    async def handle(self, handler_input):
        print("DEBUG: LaunchRequestHandler started")
        # type: (HandlerInput) -> Response
        attributes_manager = handler_input.attributes_manager
        session_attributes = attributes_manager.get_session_attributes()

        session_attributes["currentSymptomIndex"] = 0 # symptomsリストのインデックスは0から始まる
        session_attributes["recordedSymptoms"] = []
        attributes_manager.set_session_attributes(session_attributes)

        speak_output = 'こんにちは。今日の症状についてお伺いします。'
        next_symptom = symptoms[session_attributes["currentSymptomIndex"]]
        question = f"{next_symptom}はありますか？ 強い / 少し / 無い"

        print("DEBUG: Returning response from LaunchRequestHandler")
        return (
            handler_input.response_builder
                .speak(speak_output + question)
                .ask(question)
                .response
        )

class SymptomIntentHandler(AbstractRequestHandler):
    """Handler for SymptomIntent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SymptomIntent")(handler_input)

    async def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        print("DEBUG: SymptomIntentHandler started")
        attributes_manager = handler_input.attributes_manager
        session_attributes = attributes_manager.get_session_attributes()
        
        current_symptom_index = session_attributes.get("currentSymptomIndex", 0)
        recorded_symptoms = session_attributes.get("recordedSymptoms", [])
        
        # 前回の質問の症状を取得 (currentSymptomIndexは次の質問の症状を指しているので、-1する)
        current_symptom = symptoms[current_symptom_index] if current_symptom_index < len(symptoms) else None

        symptom_strength_slot = ask_utils.request_util.get_slot(handler_input, 'symptomStrength')
        symptom_strength = symptom_strength_slot.value if symptom_strength_slot else None

        speak_output = ''
        reprompt_output = ''

        if current_symptom and symptom_strength and symptom_strength != '無い':
            recorded_symptoms.append({
                "name": current_symptom,
                "strength": symptom_strength
            })
            session_attributes["recordedSymptoms"] = recorded_symptoms

        session_attributes["currentSymptomIndex"] += 1

        if session_attributes["currentSymptomIndex"] < len(symptoms):
            next_symptom = symptoms[session_attributes["currentSymptomIndex"]]
            speak_output = f"{next_symptom}はありますか？ 強い / 少し / 無い"
            reprompt_output = speak_output
        else:
            # 全ての既存症状の質問が終了
            speak_output = '全ての症状について質問し終えました。他に気になる症状はありますか？症状を自由にお話しください。'
            reprompt_output = speak_output
            session_attributes["askingNewSymptom"] = True # 新しい症状を尋ねるフラグ

        attributes_manager.set_session_attributes(session_attributes)

        print("DEBUG: Returning response from SymptomIntentHandler")
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt_output)
                .response
        )

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
            # ここで症状の分割と標準化のロジックを実装 (JS版と同様に簡易的にそのまま追加)
            identified_symptoms = [new_symptom] # 複数症状対応のため配列とする

            for symptom in identified_symptoms:
                # 症状の強さを尋ねる
                speak_output += f"{symptom}は強いですか？ 少しですか？ 無いですか？"
                reprompt_output += speak_output
                session_attributes["currentNewSymptom"] = symptom # 現在確認中の新しい症状
                session_attributes["askingNewSymptomStrength"] = True # 新しい症状の強さを尋ねるフラグ
                break # 一度に一つの症状だけ確認
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

class NewSymptomStrengthIntentHandler(AbstractRequestHandler):
    """Handler for NewSymptomStrengthIntent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("NewSymptomStrengthIntent")(handler_input)

    async def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        print("DEBUG: NewSymptomStrengthIntentHandler started")
        attributes_manager = handler_input.attributes_manager
        session_attributes = attributes_manager.get_session_attributes()
        recorded_symptoms = session_attributes.get("recordedSymptoms", [])

        new_symptom_strength_slot = ask_utils.request_util.get_slot(handler_input, 'symptomStrength')
        new_symptom_strength = new_symptom_strength_slot.value if new_symptom_strength_slot else None
        current_new_symptom = session_attributes.get("currentNewSymptom")

        if current_new_symptom and new_symptom_strength and new_symptom_strength != '無い':
            recorded_symptoms.append({
                "name": current_new_symptom,
                "strength": new_symptom_strength
            })
            session_attributes["recordedSymptoms"] = recorded_symptoms

        # 次の新しい症状があるか、または終了
        # ここでは簡易的に、新しい症状の確認フェーズを終了
        if "currentNewSymptom" in session_attributes:
            del session_attributes["currentNewSymptom"]
        if "askingNewSymptomStrength" in session_attributes:
            del session_attributes["askingNewSymptomStrength"]
        if "askingNewSymptom" in session_attributes:
            del session_attributes["askingNewSymptom"]
        
        attributes_manager.set_session_attributes(session_attributes)

        # DynamoDBに保存
        print("DEBUG: Before saving to DynamoDB in NewSymptomStrengthIntentHandler")
        persistent_attributes = await attributes_manager.get_persistent_attributes()
        if not persistent_attributes:
            persistent_attributes = {}
        
        today = date.today().isoformat() # YYYY-MM-DD
        persistent_attributes[today] = recorded_symptoms
        await attributes_manager.save_persistent_attributes()
        print("DEBUG: After saving to DynamoDB in NewSymptomStrengthIntentHandler")

        speak_output = 'ありがとうございます。今日の症状を記録しました。'
        print("DEBUG: Returning response from NewSymptomStrengthIntentHandler")
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        print("DEBUG: HelpIntentHandler started")
        speak_output = 'このスキルはあなたの症状を記録します。'
        print("DEBUG: Returning response from HelpIntentHandler")
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class CancelAndStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    async def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        print("DEBUG: CancelAndStopIntentHandler started")
        attributes_manager = handler_input.attributes_manager
        session_attributes = attributes_manager.get_session_attributes()
        recorded_symptoms = session_attributes.get("recordedSymptoms", [])

        # セッションが終了する前に記録された症状を保存
        if recorded_symptoms:
            persistent_attributes = await attributes_manager.get_persistent_attributes()
            print("DEBUG: Before saving to DynamoDB in CancelAndStopIntentHandler")
            if not persistent_attributes:
                persistent_attributes = {}
            today = date.today().isoformat() # YYYY-MM-DD
            persistent_attributes[today] = recorded_symptoms
            await attributes_manager.save_persistent_attributes()
            print("DEBUG: After saving to DynamoDB in CancelAndStopIntentHandler")

        speak_output = 'ご利用ありがとうございました。'
        print("DEBUG: Returning response from CancelAndStopIntentHandler")
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    async def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        print("DEBUG: SessionEndedRequestHandler started")
        attributes_manager = handler_input.attributes_manager
        session_attributes = attributes_manager.get_session_attributes()
        recorded_symptoms = session_attributes.get("recordedSymptoms", [])

        # セッションが終了する前に記録された症状を保存
        if recorded_symptoms:
            persistent_attributes = await attributes_manager.get_persistent_attributes()
            print("DEBUG: Before saving to DynamoDB in SessionEndedRequestHandler")
            if not persistent_attributes:
                persistent_attributes = {}
            today = date.today().isoformat() # YYYY-MM-DD
            persistent_attributes[today] = recorded_symptoms
            await attributes_manager.save_persistent_attributes()
            print("DEBUG: After saving to DynamoDB in SessionEndedRequestHandler")
            
        print("DEBUG: Returning response from SessionEndedRequestHandler")
        return handler_input.response_builder.response

class FallbackIntentHandler(AbstractRequestHandler):
    """
    This handler will not be triggered unless you have skill level intent
    routing enabled and this intent is not Dafault to any other intent.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        print("DEBUG: FallbackIntentHandler started")
        speech_text = (
            "すみません、症状記録スキルではそのリクエストを理解できませんでした。症状を記録するか、更新することができます。"
        )
        reprompt_text = "症状を記録しますか、それとも更新しますか？"
        print("DEBUG: Returning response from FallbackIntentHandler")
        return (
            handler_input.response_builder
                .speak(speech_text)
                .ask(reprompt_text)
                .response
        )

class AllExceptionHandler(AbstractExceptionHandler):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        print("DEBUG: AllExceptionHandler started")
        logger.error(exception, exc_info=True)
        speak_output = '申し訳ありません、スキルの処理中にエラーが発生しました。もう一度お試しください。'
        print("DEBUG: Returning response from AllExceptionHandler")
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# リクエストハンドラーの登録
sb = CustomSkillBuilder(persistence_adapter = dynamodb_adapter)

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SymptomIntentHandler())
sb.add_request_handler(NewSymptomIntentHandler())
sb.add_request_handler(NewSymptomStrengthIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(FallbackIntentHandler()) # 既存のFallbackIntentHandlerを残す

# 例外ハンドラーの登録
sb.add_exception_handler(AllExceptionHandler())

lambda_handler = sb.lambda_handler()
