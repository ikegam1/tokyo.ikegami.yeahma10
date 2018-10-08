import logging
import os
import random
import json
import re
import zenhan
import base64
import boto3
from datetime import datetime, timedelta
from botocore.vendored import requests
from cek import (Clova, SpeechBuilder, ResponseBuilder)
from flask import (Flask, request, jsonify)
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Flask
app = Flask(__name__)

# Clova
application_id = os.environ.get('CLOVA_APPLICATION_ID')
channel_secret = os.environ.get('CHANNEL_SECRET')
channel_access_token = os.environ.get('CHANNEL_ACCESS_TOKEN')
channel_push_url = os.environ.get('CHANNEL_PUSH_URL')
log_push_user_token = os.environ.get('LOG_PUSH_USER_TOKEN')
channel_reply_url = os.environ.get('CHANNEL_REPLY_URL')
yeahma10_table = os.environ.get('DYNAMO_YEAHMA10_TABLE')
topic_arn = os.environ.get('SNS_TOPIC_ARN') 
clova = Clova(
            application_id=application_id,
            default_language='ja',
            debug_mode=True)
speech_builder = SpeechBuilder(default_language='ja')
response_builder = ResponseBuilder(default_language='ja')
resp_attributes = {}
debugbot = False
debuglog = False

#mp3
drumrole_mp3 = "http://ikegami.tokyo/wp-content/uploads/2018/10/tympani-roll1.mp3"
question_mp3 = "http://ikegami.tokyo/wp-content/uploads/2018/10/question1.mp3"
correct_mp3 = "http://ikegami.tokyo/wp-content/uploads/2018/10/correct2.mp3"
incorrect_mp3 = "http://ikegami.tokyo/wp-content/uploads/2018/10/incorrect1.mp3"

# Quiz
import data
quiz = data._quiz

def send_line_bot(user, message):
    resp = {
                'to': user,
                'messages': [
                    {
                        "type": "text",
                        "text": message 
                    }
                ],
           }
    header = { 
                 "content-type": "application/json",
                 "Authorization": "Bearer " + channel_access_token,
             }
    res =  requests.post(
               channel_push_url,
               headers=header,
               data=json.dumps(resp),
           )
    logger.info(str(res))
    return res

def send_line_bot_log(user, message):
    user = LOG_PUSH_USER_TOKEN
    resp = {
                'to': user,
                'messages': [
                    {
                        "type": "text",
                        "text": message 
                    }
                ],
           }
    header = { 
                 "content-type": "application/json",
                 "Authorization": "Bearer " + channel_access_token,
             }
    res =  requests.post(
               channel_push_url,
               headers=header,
               data=json.dumps(resp),
           )
    logger.info(str(res))
    return res




@app.route('/', methods=['GET'])
def lambda_handler(event=None, context=None):
    logger.info('Lambda function invoked index()')

    return 'hello from Flask!'


if __name__ == '__main__':
    app.run(debug=True)

@app.route('/', methods=['POST'])
def clova_service():
    logger.info('clova_service()')
    strreq = request.data
    try:
        strreq = strreq.decode()
    except AttributeError:
        pass
    jsonreq = json.loads(strreq)

    if debugbot:
        logger.info(strreq)
        send_line_bot(jsonreq['session']['user']['userId'], str(strreq))
    resp = clova.route(request.data, request.headers)
    resp = jsonify(resp)

    resp.headers['Content-Type'] = 'application/json;charset-UTF-8'
    return resp

@clova.handle.intent('QuizIntent')
def quiz_intent_handler(clova_request):
    attributes = clova_request.session_attributes
    resp_attributes = set_qacount(attributes)
    if 'quiz' in attributes:
        return quizin_intent_handler(clova_request)
    elif 'answer' in attributes:
        return answer_intent_handler(clova_request)

    if debuglog:
        logger.info('QuizIntent')
        logger.info(clova_request)

    if 'history' in attributes:
        for his in attributes['history']:
            for i in range(len(quiz)):
                if quiz[i-1]['key'] == int(his):
                    del quiz[i-1]

    if len(quiz) < 1:
        text = f"・・あれ？問題がもうなくなっちゃいました。遊んでくれてありがとう。{attributes['cntq']}問中、{attributes['cnta']}問正解だったよ！またやってね！"
        response =  response_builder.simple_speech_text(text, 'ja', True)
        response.session_attributes = {}
        return response

    currentQuiz = random.choice(quiz)
    text = currentQuiz["chanq"] + 'って10回言ってみて！'
    response = response_builder.simple_speech_text(text)
    if debuglog:
        logger.info(response)
    response = response_builder.add_reprompt(response, speech_builder.simple_speech(speech_builder.plain_text(currentQuiz["chanq"] + 'だよ。10回ね')))
    resp_attributes['quiz'] = currentQuiz
    response.session_attributes = resp_attributes

    return response

@clova.handle.intent('QuizInIntent')
def quizin_intent_handler(clova_request):
    attributes = clova_request.session_attributes
    resp_attributes = set_qacount(attributes)
    text = ''
    response = None
    if 'quiz' in attributes:
        text = attributes["quiz"]
    else:
        return quiz_intent_handler(clova_request)

    try:
        if 'InductionSlot' in clova_request.slots_dict and 'InductionSlot_f' in clova_request.slots_dict \
                and 'InductionSlot_g' in clova_request.slots_dict and 'InductionSlot_h' in clova_request.slots_dict \
                and 'InductionSlot_b' in clova_request.slots_dict and 'InductionSlot_c' in clova_request.slots_dict \
                and 'InductionSlot_d' in clova_request.slots_dict and 'InductionSlot_e' in clova_request.slots_dict:
            induction = clova_request.slot_value('InductionSlot')
            induction_b = clova_request.slot_value('InductionSlot_b')
            induction_c = clova_request.slot_value('InductionSlot_c')
            induction_d = clova_request.slot_value('InductionSlot_d')
            induction_e = clova_request.slot_value('InductionSlot_e')
            induction_f = clova_request.slot_value('InductionSlot_f')
            induction_g = clova_request.slot_value('InductionSlot_g')
            induction_h = clova_request.slot_value('InductionSlot_h')
            logger.info(str(induction)+str(induction_h))
            if len(induction) > 0 and len(induction_b) > 0 and len(induction_h) > 0 and induction == text['chanq']:
                values = []
                values.append(speech_builder.url(question_mp3))
                values.append(speech_builder.plain_text(text['q']))
                response = response_builder.speech_list(values)
                response = response_builder.add_reprompt(response, speech_builder.simple_speech(speech_builder.plain_text('３。。。。。２。。。。。１。。。')))
                resp_attributes['answer'] =  attributes["quiz"]
                response.session_attributes = resp_attributes
        else:
            _texts = ["ごめんなさい。聞き取れなかったです。もう一度言ってくださいね。"]
            _texts.append("聞き取るの難しいです・・・。少しゆっくり言ってみてね。")
            _texts.append("ごめんなさい。わかりません・・・。やりなおす時は、「最初からやる」といってくださいね。")
            _texts.append("聞き取れなかったです・・・。もう少しだけClovaに近づいて言ってみてね。")
            _texts.append("ごめんなさい。わかりません・・・。周りは静かですか？もう一度言ってみてください。")
            response = response_builder.simple_speech_text(random.choice(_texts))
            response = response_builder.add_reprompt(response, speech_builder.simple_speech(speech_builder.plain_text(text['chanq'] + 'を10回、言ってみて')))
            resp_attributes['quiz'] =  attributes["quiz"]
            response.session_attributes = resp_attributes
        return response
    except TypeError:
        pass

    response = response_builder.simple_speech_text("聞き取れなかったです。もう一度言ってくださいね。やりなおしたい時は、「最初からやる」といってくださいね。")
    resp_attributes['quiz'] =  attributes["quiz"]
    response.session_attributes = resp_attributes
    return response

@clova.handle.intent('AnswerIntent')
def answer_intent_handler(clova_request):
    attributes = clova_request.session_attributes
    resp_attributes = set_qacount(attributes)
    text = ''
    if 'answer' in attributes:
        text = attributes["answer"]
    elif 'quiz' in attributes:
        return quizin_intent_handler(clova_request)
    else:
        return quiz_intent_handler(clova_request)

    values = []
    values.append(speech_builder.url(drumrole_mp3))
    if 'answer' in clova_request.slots_dict:
        if clova_request.slot_value('answer') in attributes["answer"]["a"]:
            logger.info(str(resp_attributes))
            prize = ['すごい！','アメージング！','素晴らしい！','なかなかやりますね','グレイト！']
            text = "正解は・・・" + clova_request.slot_value('answer')+ "です！"
            text += f"・・{random.choice(prize)}！。"
            text += '次の問題もやりますか？'
            resp_attributes['cntq'] += 1
            resp_attributes['cnta'] += 1
            values.append(speech_builder.url(correct_mp3))
            values.append(speech_builder.plain_text(text))
        else:
            text = '・・んー、残念！はずれです！。'
            text += "正解は・・・" + attributes["answer"]["a"][0] + "でした。"
            text += '次の問題もやりますか？'
            resp_attributes['cntq']+=1
            values.append(speech_builder.url(incorrect_mp3))
            values.append(speech_builder.plain_text(text))
    else:
        text = '・・んー、残念！はずれです！'
        text += "正解は・・・" + attributes["answer"]["a"][0] + "でした。"
        text += '次の問題もやる？'
        resp_attributes['cntq']+=1
        values.append(speech_builder.url(incorrect_mp3))
        values.append(speech_builder.plain_text(text))

    response = response_builder.speech_list(values)
    response = response_builder.add_reprompt(response, speech_builder.simple_speech(speech_builder.plain_text('「はい」か「いいえ」で答えてね')))
    resp_attributes['retry'] =  True
    if 'history' in resp_attributes:
        resp_attributes['history'].append(attributes["answer"]["key"])
    else:
        resp_attributes['history'] = [attributes["answer"]["key"]]
    response.session_attributes = resp_attributes
    return response

@clova.handle.intent('HelloIntent')
def hello_intent_handler(clova_request):
    attributes = clova_request.session_attributes
    resp_attributes = set_qacount(attributes)
    text = "言えまてんクイズです。これから言う言葉を10回言った後、クイズに答えてね。ではスタートと言ってください。"
    response = response_builder.simple_speech_text(text)
    response.session_attributes = resp_attributes
    response = response_builder.add_reprompt(response, speech_builder.simple_speech(speech_builder.plain_text('スタートというとはじまるよ')))
    logger.info(response)
    if debugbot:
        send_line_bot_log(clova_request.user_id, str(response))

    return response

@clova.handle.launch
def launch_request_handler(clova_request):
    return hello_intent_handler(clova_request)

@clova.handle.intent('Clova.GuideIntent')
def guide_intent_handler(clova_request):
    return default_handler(clova_request)


@clova.handle.intent('YesIntent')
def yes_intent_handler(clova_request):
    attributes = clova_request.session_attributes
    resp_attributes = set_qacount(attributes)
    response = response_builder.simple_speech_text('もう一度お願いします')
    response.session_attributes = resp_attributes
    text = ''
    if 'retry' in attributes:
        return quiz_intent_handler(clova_request)
    else:
        return response

@clova.handle.intent('Clova.YesIntent')
def clova_yes_intent_handler(clova_request):
    return yes_intent_handler(clova_request)
    

@clova.handle.intent('NoIntent')
def no_intent_handler(clova_request):
    attributes = clova_request.session_attributes
    cntq = 0
    cnta = 0
    history = []
    text = ""
    if 'cntq' in attributes:
        cntq = attributes['cntq']
        cnta = attributes['cnta']

    if cntq > 0:
        text = f"遊んでくれてありがとう。{cntq}問中、{cnta}問正解だったよ！またやってね！"
    else:
        text = f"遊んでくれてありがとう。またやってね！"

    if cntq > 0:
        strHis = ""
        history = attributes['history']
        for his in history:
            strHis = strHis + '問題' + str(int(his)) + '、'

        user_id = clova_request.user_id
        okng = getIntent(user_id, "follow")
        if 'message' in okng:
            if okng['message'] == 'ok' and clova_request.request_type != "SessionEndedRequest":
                text = f"遊んでくれてありがとう。{cntq}問中、{cnta}問正解だったよ！言えまてんボットに結果を通知するね！"
                res = f"「言えまてんクイズ」で遊んでくれてありがとう。{cntq}問中、{cnta}問正解だったよ！"
                send_line_bot(user_id, res)
                res = "今回の問題は、" +  strHis + "でした。「問題" + str(int(history[0])) + "の答え」のようにBotに言ってみてね。"
                send_line_bot(user_id, res)

    response =  response_builder.simple_speech_text(text, 'ja', True)
    return response

@clova.handle.intent('Clova.NoIntent')
def clova_no_intent_handler(clova_request):
    return no_intent_handler(clova_request)

@clova.handle.intent('Clova.CancelIntent')
def cancel_intent_handler(clova_request):
    return no_intent_handler(clova_request)

@clova.handle.intent('FinishIntent')
def finish_intent_handler(clova_request):
    return no_intent_handler(clova_request)

@clova.handle.launch
def launch_handler(clova_request):
    text = "言えまてんクイズです。これから言う言葉を10回言った後、クイズに答えてね。ではスタートと言ってください。"
    response = response_builder.simple_speech_text(text)
    response.session_attributes = set_qacount({})
    response = response_builder.add_reprompt(response, speech_builder.simple_speech(speech_builder.plain_text('スタートというとはじまるよ')))
    logger.info(response)
    if debugbot:
        send_line_bot_log(clova_request.user_id, str(response))

    return response

@clova.handle.default
def default_handler(clova_request):
    attributes = {}
    try:
        attributes = clova_request.session_attributes
    except AttributeError:
        response.session_attributes = attributes 
    resp_attributes = set_qacount(attributes)
    logger.info(clova_request)
    text = ''

    if clova_request.request_type == "SessionEndedRequest":
            return no_intent_handler(clova_request)
    elif not clova_request.is_intent:
        return hello_intent_handler(clova_request)
    elif 'quiz' in attributes:
        text = attributes["quiz"]
        return quizin_intent_handler(clova_request)
    elif 'answer' in attributes:
        text = attributes["answer"]
        return answer_intent_handler(clova_request)
    elif not clova_request.is_intent:
        return hello_intent_handler(clova_request)

    response =  response_builder.simple_speech_text('もう一度お願いします')
    response.session_attributes = attributes 
    return response

@clova.handle.end
def end_intent_handler(clova_request):
    logger.info('handle.end')
    return no_intent_handler(clova_request)

def set_qacount(att):
    cntq = 0
    cnta = 0
    history = []
    if 'cntq' in att:
        cntq = int(att['cntq'])
        cnta = int(att['cnta'])
    if 'history' in att:
        history = att['history']

    resp_attributes = {}
    resp_attributes['cntq'] = cntq
    resp_attributes['cnta'] = cnta
    resp_attributes['history'] = history
    return resp_attributes

"""messageing api"""
@app.route('/message/', methods=['POST'])
def messaging_service():
    logger.info('messaging_service()')

    strreq = request.data
    try:
        strreq = strreq.decode()
    except AttributeError:
        pass
    jsonreq = json.loads(strreq)
    if debuglog:
        logger.info(str(jsonreq))
    reply_token = ''
    message = ''
    strMessage = ''
    user_id = ''
    etype = ''
    postbackdata = ''
    timestamp = datetime.now()

    for e in jsonreq['events']:
        etype = e['type']
        reply_token = e['replyToken']
        user_id = e['source']['userId']
        if etype == 'message':
            message = e['message']
            strMessage = message['text']
            timestamp = int(e['timestamp'])
        elif etype == 'follow':
            timestamp = int(e['timestamp'])
        elif etype == 'postback':
            logger.info(str(e))
            postbackdata = e['postback']['data']
            timestamp = int(e['timestamp'])

    date = datetime.now()
    send_line_bot_log(user_id, f"{user_id},{strMessage}," + date.strftime('%Y/%m/%d %H:%M:%S'))
    strIntent = ""
    _i = " "
    _q = " "
    _a = " "
    _n = " "

    #followevent
    if etype == 'follow' or strMessage == u'クイズ連携':
        send_line_bot_log(user_id, f"{user_id},follow message," + date.strftime('%Y/%m/%d %H:%M:%S'))
        mess = []
        mess.append("言えまてんBotです！フォローありがとう！")
        mess.append({
                 'type': 'template',
                 'altText': '確認',
                 'template' : {
                     'type': 'confirm',
                     'text': 'Clovaはお持ちですか？言えまてんクイズからのメッセージをこちらに送信しても大丈夫ですか？',
                     'actions': [
                         {
                             'type': 'postback',
                             'label': 'はい',
                             'data': 'res=yes'
                         },
                         { 
                             'type': 'postback',
                             'label': 'いいえ',
                             'data': 'res=no'
                         }
                     ]
                }
            })
        send_line_reply(reply_token, mess)

    if etype == 'postback':
        if postbackdata == 'res=yes':
            text = "ありがとう！言えまてんクイズの使い方を知りたい時は「使い方」と言ってみてね！"
            send_line_reply(reply_token, text)
            insert(user_id, "follow",  "follow", "ok" ,_i,_q,_a,_n)
        else:
            text = "残念です！言えまてんクイズの使い方を知りたい時は「使い方」と言ってみてね！"
            send_line_reply(reply_token, text)
            insert(user_id, "follow",  "follow", "ng" ,_i,_q,_a,_n)
        return True


    intent = getIntent(user_id, "reply")
    if 'date' in intent:
        postDate = intent['date']
        if datetime.strptime(postDate , '%Y/%m/%d %H:%M:%S') > datetime.now() - timedelta(hours=1):
            strIntent = intent['intent']
            _i = intent['induction'] 
            _q = intent['quiz'] 
            _a = intent['answer'] 
    

    if re.compile("こんにちは|Hello|こんばんは|おはよう").search(message['text']):
        text = "こんにちは！言えまてんボットです。よろしくね。「使い方」というと説明するよ！"
        send_line_reply(reply_token, text)
    elif re.compile("使い方|つかいかた|Help|ヘルプ").search(message['text']):
        mess =  u'言えまてんクイズの使い方です。最初にひとつの言葉を10回繰り返して言ってもらいます。\n'
        mess += u'次に、その言葉に少し関係のある問題を出すので答えを考えてね。問題は全部で' + str(len(quiz)) + 'つありますよ。\n'
        mess += u'答えがあっていると正解！です。もう一度問題をやるか聞かれたら「はい」か「いいえ」と答えてね。\n'
        mess += u'「問題1」、「問題1の答え」のようにBotに言うと問題についてお答えします。問題を思いついた人は「応募」と言ってみてね。\n'
        send_line_reply(reply_token,mess) 
    elif strIntent == "post1" and len(message['text']) > 1:
        _i = message['text']
        insert(user_id, "reply",  "post2", message,_i,_q,_a,_n)
        mess = []
        mess.append( "「" + message['text'] + "」ですね。わかりました。")
        mess.append( "次に問題を教えてください。")
        send_line_reply(reply_token,mess) 
    elif strIntent == "post2" and len(message['text']) > 5:
        _q = message['text']
        insert(user_id, "reply",  "post3", message,_i,_q,_a,_n)
        mess = []
        mess.append( "問題は「" + message['text'] + "」ですね。わかりました。")
        mess.append( "次は答えを教えてください。")
        send_line_reply(reply_token,mess) 
    elif strIntent == "post3" and len(message['text']) > 0:
        _a = message['text']
        insert(user_id, "reply",  "post4", message,_i,_q,_a,_n)
        mess = []
        mess.append( "答えは「" + message['text'] + "」ですね。わかりました。")
        mess.append( "最後にニックネームを教えて！もし採用されたら問題の解説の時に紹介するね。内緒にしたい時は「匿名」と答えてね。")
        send_line_reply(reply_token,mess) 
    elif strIntent == "post4" and len(message['text']) > 0:
        _n = message['text']
        insert(user_id, "reply",  "finish", message,_i,_q,_a,_n)
        mess = []
        mess.append( "「" + message['text'] + "」さん、応募ありがとう！")
        mess.append( "参考にするね！")
        send_line_reply(reply_token,mess) 
        send_sns(str(jsonreq), _i, _q, _a, _n)
    elif re.compile("応募|おうぼ|投稿").search(message['text']):
        insert(user_id, "reply",  "post1", message,_i,_q,_a,_n)
        mess = []
        mess.append( "言えまてんクイズです。新しい問題を応募してます。面白い問題を考えた人は、1.10回繰り返す言葉(キリンとか)、2.問題、3.答えの3つを教えてね。")
        mess.append( "では、10回繰り返して言ってもらうフレーズを教えてください。")
        send_line_reply(reply_token, mess)
    elif re.compile("^問題[0-9]{1,2}$").search(zenhan.z2h(message['text'])):
        match = re.compile("[0-9]{1,2}").search(zenhan.z2h(message['text']))
        num = int(match.group())
        if num > 0:
            if len(quiz) >= num:
                text = f"問題{num}: {quiz[num]['q']}"
                send_line_reply(reply_token,text) 
            else:
                text = f"問題{num}がみつかりません。"
                send_line_reply(reply_token,text) 
    elif re.compile("^問題[0-9]{1,2}の答").search(zenhan.z2h(message['text'])):
        match = re.compile("[0-9]{1,2}").search(zenhan.z2h(message['text']))
        num = int(match.group())
        if num > 0:
            if len(quiz) >= num:
                mess = []
                mess.append(f"問題{num}の答え=> {quiz[num]['a'][0]}")
                mess.append(f"問題{num}の解説=> {quiz[num]['i']}")
                send_line_reply(reply_token,mess) 
            else:
                text = f"問題{num}がみつかりません。"
                send_line_reply(reply_token,text) 

    return True


def send_line_reply(token, message):
    messages = []
    if isinstance(message, list):
        for mess in message:
            if isinstance(mess, dict):
                messages.append(mess)
            else:
                messages.append({ "type": "text", "text": mess })
    else:
        messages.append({ "type": "text", "text": message })

    resp = {
                'replyToken': token,
                'messages': messages
           }
    header = { 
                 "content-type": "application/json",
                 "Authorization": "Bearer " + channel_access_token,
             }
    res =  requests.post(
               channel_reply_url,
               headers=header,
               data=json.dumps(resp),
           )
    logger.info(str(res))
    return res

def insert(userId, event, intent, message, _i='', _q='', _a='', _n=''):
    date = datetime.now() + timedelta(hours=9)
    table = dynamodb.Table(yeahma10_table)
    try:
        res = table.put_item(
                  Item = {
                      "userId": userId,
                      "event": event,
                      "date": date.strftime("%Y/%m/%d %H:%M:%S"),
                      "intent": intent,
                      "message": message,
                      "induction": _i,
                      "nickname": _n,
                      "quiz": _q,
                      "answer": _a
                  }
              )
    except ClientError as e:
        logging.log(100, e.response['Error']['Message'])
        logging.log(100, e.response['Error']['Code'])
        return False 
    else:
        logging.log(100, str(res))
        return res

def getIntent(userId,event):
    table = dynamodb.Table(yeahma10_table)
    item = {}
    try:
        res = table.get_item(
            Key = {
                "userId": userId,
                "event": event
            }
        )
        logging.log(100,res)
    except ClientError as e:
        logging.log(100, e.response['Error']['Message'])
        logging.log(100, e.response['Error']['Code'])
        item['intent'] = ""
        return item
    else:
        logging.log(100,str(res))
        item = res.get('Item',{'intent':''})
        return item

def send_sns(_o,_i,_q,_a,_n):
    client = boto3.client('sns')
    _s = u'言えまてんの応募がありました'
    _m = _i + '\n'
    _m += _q + '\n'
    _m += _a + '\n'
    _m += _n + '\n'
    _m += '\n' + str(_o) + '\n'
    req = {
        'TopicArn': topic_arn,
        'Message': _m,
        'Subject': _s
        }
    res = client.publish(**req)

    return res


