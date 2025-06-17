const Alexa = require('ask-sdk-core');
const ddbAdapter = require('ask-sdk-dynamodb-persistence-adapter');

const AWS = require("aws-sdk");

const symptoms = ['発熱', 'めまい', '倦怠感', '吐き気', '頭痛', '咳', '鼻水', '喉の痛み', '関節痛', '筋肉痛', '食欲不振', '下痢', '便秘', '不眠'];

const LaunchRequestHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'LaunchRequest';
    },
    async handle(handlerInput) {
        const { attributesManager } = handlerInput;
        const sessionAttributes = attributesManager.getSessionAttributes();

        sessionAttributes.currentSymptomIndex = 1;
        sessionAttributes.recordedSymptoms = [];
        attributesManager.setSessionAttributes(sessionAttributes);

        const speakOutput = 'こんにちは。今日の症状についてお伺いします。';
        const nextSymptom = symptoms[sessionAttributes.currentSymptomIndex];
        const question = `${nextSymptom}はありますか？ 強い / 少し / 無い`;

        return handlerInput.responseBuilder
            .speak(speakOutput + question)
            .reprompt(question)
            .getResponse();
    }
};

const SymptomIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'SymptomIntent';
    },
    async handle(handlerInput) {
        const { attributesManager, requestEnvelope } = handlerInput;
        const sessionAttributes = attributesManager.getSessionAttributes();
        const persistentAttributes = await attributesManager.getPersistentAttributes() || {};

        const currentSymptomIndex = sessionAttributes.currentSymptomIndex;
        const recordedSymptoms = sessionAttributes.recordedSymptoms;
        const currentSymptom = symptoms[currentSymptomIndex - 1]; // 前回の質問の症状

        const symptomStrengthSlot = Alexa.getSlot(requestEnvelope, 'symptomStrength'); // スロット名 'symptomStrength' を想定
        const symptomStrength = symptomStrengthSlot && symptomStrengthSlot.value;

        let speakOutput = '';
        let repromptOutput = '';

        if (currentSymptom && symptomStrength && symptomStrength !== '無い') {
            recordedSymptoms.push({
                name: currentSymptom,
                strength: symptomStrength
            });
        }

        if (currentSymptomIndex < symptoms.length) {
            const nextSymptom = symptoms[currentSymptomIndex];
            speakOutput = `${nextSymptom}はありますか？ 強い / 少し / 無い`;
            repromptOutput = speakOutput;
            sessionAttributes.currentSymptomIndex = currentSymptomIndex + 1;
        } else {
            // 全ての既存症状の質問が終了
            speakOutput = '全ての症状について質問し終えました。他に気になる症状はありますか？症状を自由にお話しください。';
            repromptOutput = speakOutput;
            sessionAttributes.askingNewSymptom = true; // 新しい症状を尋ねるフラグ
        }

        attributesManager.setSessionAttributes(sessionAttributes);

        return handlerInput.responseBuilder
            .speak(speakOutput)
            .reprompt(repromptOutput)
            .getResponse();
    }
};

const NewSymptomIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'NewSymptomIntent'; // 新しい症状を登録するインテントを想定
    },
    async handle(handlerInput) {
        const { attributesManager, requestEnvelope } = handlerInput;
        const sessionAttributes = attributesManager.getSessionAttributes();
        const persistentAttributes = await attributesManager.getPersistentAttributes() || {};

        const newSymptomSlot = Alexa.getSlot(requestEnvelope, 'newSymptom'); // 新しい症状のスロット名 'newSymptom' を想定
        const newSymptom = newSymptomSlot && newSymptomSlot.value;

        let speakOutput = '';
        let repromptOutput = '';

        if (newSymptom) {
            // ここで症状の分割と標準化のロジックを実装
            // 現時点では簡易的にそのまま追加
            const identifiedSymptoms = [newSymptom]; // 複数症状対応のため配列とする

            for (const symptom of identifiedSymptoms) {
                // 症状の強さを尋ねる
                speakOutput += `${symptom}は強いですか？ 少しですか？ 無いですか？`;
                repromptOutput += speakOutput;
                sessionAttributes.currentNewSymptom = symptom; // 現在確認中の新しい症状
                sessionAttributes.askingNewSymptomStrength = true; // 新しい症状の強さを尋ねるフラグ
                break; // 一度に一つの症状だけ確認
            }
        } else {
            speakOutput = '申し訳ありません、症状が聞き取れませんでした。もう一度お話しください。';
            repromptOutput = speakOutput;
        }

        attributesManager.setSessionAttributes(sessionAttributes);

        return handlerInput.responseBuilder
            .speak(speakOutput)
            .reprompt(repromptOutput)
            .getResponse();
    }
};

const NewSymptomStrengthIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'NewSymptomStrengthIntent'; // 新しい症状の強さを登録するインテントを想定
    },
    async handle(handlerInput) {
        const { attributesManager, requestEnvelope } = handlerInput;
        const sessionAttributes = attributesManager.getSessionAttributes();
        const recordedSymptoms = sessionAttributes.recordedSymptoms;

        const newSymptomStrengthSlot = Alexa.getSlot(requestEnvelope, 'symptomStrength'); // スロット名 'symptomStrength' を想定
        const newSymptomStrength = newSymptomStrengthSlot && newSymptomStrengthSlot.value;
        const currentNewSymptom = sessionAttributes.currentNewSymptom;

        let speakOutput = '';
        let repromptOutput = '';

        if (currentNewSymptom && newSymptomStrength && newSymptomStrength !== '無い') {
            recordedSymptoms.push({
                name: currentNewSymptom,
                strength: newSymptomStrength
            });
            sessionAttributes.recordedSymptoms = recordedSymptoms;
        }

        // 次の新しい症状があるか、または終了
        // ここでは簡易的に、新しい症状の確認フェーズを終了
        delete sessionAttributes.currentNewSymptom;
        delete sessionAttributes.askingNewSymptomStrength;
        delete sessionAttributes.askingNewSymptom;

        // DynamoDBに保存
        const persistentAttributes = await attributesManager.getPersistentAttributes() || {};
        const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
        persistentAttributes[today] = recordedSymptoms;
        await attributesManager.setPersistentAttributes(persistentAttributes);
        await attributesManager.savePersistentAttributes();

        speakOutput = 'ありがとうございます。今日の症状を記録しました。';
        return handlerInput.responseBuilder
            .speak(speakOutput)
            .getResponse();
    }
};


const HelpIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.HelpIntent';
    },
    handle(handlerInput) {
        const speakOutput = 'このスキルはあなたの症状を記録します。';

        return handlerInput.responseBuilder
            .speak(speakOutput)
            .reprompt(speakOutput)
            .getResponse();
    }
};

const CancelAndStopIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && (Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.CancelIntent'
                || Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.StopIntent');
    },
    async handle(handlerInput) {
        const { attributesManager } = handlerInput;
        const sessionAttributes = attributesManager.getSessionAttributes();
        const recordedSymptoms = sessionAttributes.recordedSymptoms;

        // セッションが終了する前に記録された症状を保存
        if (recordedSymptoms && recordedSymptoms.length > 0) {
            const persistentAttributes = await attributesManager.getPersistentAttributes() || {};
            const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
            persistentAttributes[today] = recordedSymptoms;
            await attributesManager.setPersistentAttributes(persistentAttributes);
            await attributesManager.savePersistentAttributes();
        }

        const speakOutput = 'ご利用ありがとうございました。';
        return handlerInput.responseBuilder
            .speak(speakOutput)
            .getResponse();
    }
};

const SessionEndedRequestHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'SessionEndedRequest';
    },
    async handle(handlerInput) {
        const { attributesManager } = handlerInput;
        const sessionAttributes = attributesManager.getSessionAttributes();
        const recordedSymptoms = sessionAttributes.recordedSymptoms;

        // セッションが終了する前に記録された症状を保存
        if (recordedSymptoms && recordedSymptoms.length > 0) {
            const persistentAttributes = await attributesManager.getPersistentAttributes() || {};
            const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
            persistentAttributes[today] = recordedSymptoms;
            await attributesManager.setPersistentAttributes(persistentAttributes);
            await attributesManager.savePersistentAttributes();
        }

        return handlerInput.responseBuilder.getResponse();
    }
};

const IntentReflectorHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest';
    },
    handle(handlerInput) {
        const intentName = Alexa.getIntentName(handlerInput.requestEnvelope);
        const speakOutput = `${intentName}が呼び出されました。`;

        return handlerInput.responseBuilder
            .speak(speakOutput)
            .getResponse();
    }
};

const ErrorHandler = {
    canHandle() {
        return true;
    },
    handle(handlerInput, error) {
        console.log(`Error handled: ${error.message}`);
        const speakOutput = '申し訳ありません、スキルの処理中にエラーが発生しました。もう一度お試しください。';

        return handlerInput.responseBuilder
            .speak(speakOutput)
            .reprompt(speakOutput)
            .getResponse();
    }
};

exports.handler = Alexa.SkillBuilders.custom()
    .addRequestHandlers(
        LaunchRequestHandler,
        SymptomIntentHandler,
        NewSymptomIntentHandler,
        NewSymptomStrengthIntentHandler,
        HelpIntentHandler,
        CancelAndStopIntentHandler,
        SessionEndedRequestHandler,
        IntentReflectorHandler
    )
    .addErrorHandlers(ErrorHandler)
    .withPersistenceAdapter(
        new ddbAdapter.DynamoDbPersistenceAdapter({
            tableName: process.env.DYNAMODB_PERSISTENCE_TABLE_NAME,
            createTable: false,
            dynamoDBClient: new AWS.DynamoDB({apiVersion: 'latest', region: process.env.DYNAMODB_PERSISTENCE_REGION})
        })
    )
    .lambda();