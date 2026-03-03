import os
import json
import base64
import asyncio
import websockets
import uuid
import time
import io
import traceback
import hashlib
from fastapi import FastAPI, WebSocket, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from datetime import datetime as dt, timedelta, timezone
import jwt
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream, Parameter
from dotenv import load_dotenv
from pydub import AudioSegment
import audioop
from contextlib import suppress
from prompts import function_call_tools, build_system_message
from utils import *
import httpx
from call_log_apis import *
from customer_card_tools import (
    verify_customer_by_cnic,
    confirm_physical_custody,
    verify_tpin,
    verify_card_details,
    activate_card,
    update_customer_tpin,
    transfer_to_ivr_for_pin,
    transfer_to_agent,
    get_customer_status,
    reset_verification_attempts
)
from rag_tools import search_knowledge_base

from src.utils.audio_transcription import transcribe_audio, analyze_call_with_llm

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = 7000

VOICE = 'echo'

LOG_EVENT_TYPES = [
    'response.content.done', 'input_audio_buffer.committed',
    'session.created', 'conversation.item.deleted', 'conversation.item.created'
]

WARNING_EVENT_TYPES = [
    'error', 'rate_limits.updated'
]

SHOW_TIMING_MATH = False
call_recordings = {}

app = FastAPI()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "meezanbank-ai-call-center-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

USERS_DB = {
    "admin": {
        "username": "admin",
        "password": "admin1234",
        "full_name": "Administrator"
    },
    "demo": {
        "username": "demouser",
        "password": "demouser1234",
        "full_name": "Demo User"
    },
    "meezanbank": {
        "username": "meezanbank",
        "password": "meezanbank1234",
        "full_name": "Meezan Bank Team"
    }
}

from fastapi.staticfiles import StaticFiles
app.mount("/client", StaticFiles(directory="static", html=True), name="client")

CHANNELS = 1
RATE = 8000

call_metadata: dict[str, dict] = {}

@app.get("/", response_class=HTMLResponse)
async def index_page():
    with open("static/voice-client.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return html_content

from fastapi import Body

AVAILABLE_VOICES = {
    'echo': {
        'name': 'Saad',
        'age': 'Young Male',
        'personality': 'Warm, Friendly and Engaging'
    }
}


@app.post("/start-browser-call")
async def start_browser_call(request: Request, payload: dict = Body(...)):
    token = get_token_from_request(request)
    user_data = verify_jwt_token(token)

    phone = payload.get("phone", "webclient")
    voice = payload.get("voice", "echo")
    temperature = payload.get("temperature", 0.8)
    speed = payload.get("speed", 1.05)

    if voice not in AVAILABLE_VOICES:
        voice = "echo"

    temperature = max(0.0, min(1.2, float(temperature)))
    speed = max(0.5, min(2.0, float(speed)))

    print(f"🎙️ Voice selected: {voice} ({AVAILABLE_VOICES[voice]['name']})")
    print(f"🌡️ Temperature: {temperature}")
    print(f"⚡ Speed: {speed}x")

    call_id = await register_call(phone)
    call_id = str(call_id)
    call_recordings[call_id] = {"incoming": [], "outgoing": [], "start_time": time.time()}
    call_metadata[call_id] = {
        "phone": phone,
        "language_id": payload.get("language_id", 1),
        "voice": voice,
        "temperature": temperature,
        "speed": speed
    }
    await update_call_status(int(call_id), "pick")
    return {
        "call_id": call_id,
        "voice": voice,
        "temperature": temperature,
        "speed": speed
    }


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    form = await request.form()
    caller_number = form.get("From")
    print("Call is coming from", caller_number)
    call_id = await register_call(caller_number)
    call_id = str(call_id)
    print("call id received is", call_id, type(call_id))

    call_recordings[call_id] = {"incoming": [], "outgoing": [], "start_time": time.time()}

    call_metadata[call_id] = {
        "phone": caller_number,
        "language_id": 1,
        "voice": "echo",
        "temperature": 0.8,
        "speed": 1.05
    }

    response = VoiceResponse()
    response.say("This call may be recorded for quality purposes.", voice='Polly.Danielle-Generative', language='en-US')
    response.pause(length=1)
    host = request.url.hostname

    connect = Connect()
    stream = Stream(url=f"wss://{host}/media-stream")
    stream.parameter(name="call_id", value=call_id)
    connect.append(stream)
    response.append(connect)

    return HTMLResponse(content=str(response), media_type="application/xml")


import wave
import audioop
import io
import base64
import websockets as ws_client
from fastapi import WebSocket

USER_AUDIO_DIR = "recordings/user"
AGENT_AUDIO_DIR = "recordings/agent"
os.makedirs(USER_AUDIO_DIR, exist_ok=True)
os.makedirs(AGENT_AUDIO_DIR, exist_ok=True)
import struct
import wave
import struct


last_agent_response_time = None

def generate_silence(duration_sec, sample_rate=8000):
    num_samples = int(duration_sec * sample_rate)
    silence_pcm = b'\x00\x00' * num_samples
    return silence_pcm


async def execute_function_call(func_name: str, func_args: dict) -> dict:
    try:
        if func_name == "search_knowledge_base":
            return await search_knowledge_base(query=func_args.get("query", ""))

        elif func_name == "verify_customer_by_cnic":
            return await verify_customer_by_cnic(cnic=func_args.get("cnic", ""))

        elif func_name == "confirm_physical_custody":
            return await confirm_physical_custody(
                cnic=func_args.get("cnic", ""),
                has_card=func_args.get("has_card", False)
            )

        elif func_name == "verify_tpin":
            return await verify_tpin(
                cnic=func_args.get("cnic", ""),
                tpin=func_args.get("tpin", "")
            )

        elif func_name == "verify_card_details":
            return await verify_card_details(
                cnic=func_args.get("cnic", ""),
                last_four_digits=func_args.get("last_four_digits", ""),
                expiry_date=func_args.get("expiry_date", "")
            )

        elif func_name == "activate_card":
            return await activate_card(cnic=func_args.get("cnic", ""))

        elif func_name == "update_customer_tpin":
            return await update_customer_tpin(
                cnic=func_args.get("cnic", ""),
                new_tpin=func_args.get("new_tpin", "")
            )

        elif func_name == "transfer_to_ivr_for_pin":
            return await transfer_to_ivr_for_pin()

        elif func_name == "transfer_to_agent":
            return await transfer_to_agent(
                cnic=func_args.get("cnic", ""),
                reason=func_args.get("reason", "")
            )

        elif func_name == "get_customer_status":
            return await get_customer_status(cnic=func_args.get("cnic", ""))

        else:
            return {
                "success": False,
                "error": f"Unknown function: {func_name}",
                "message": "Function not found in the system."
            }

    except Exception as e:
        print(f"❌ Error executing function {func_name}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"An error occurred while executing {func_name}."
        }

@app.websocket("/media-stream-browser")
async def media_stream_browser(websocket: WebSocket):
    await websocket.accept()

    openai_url = 'wss://api.openai.com/v1/realtime?model=gpt-realtime-2025-08-28'
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "OpenAI-Beta": "realtime=v1"
    }

    async with ws_client.connect(openai_url, additional_headers=headers) as openai_ws:
        session_initialized = False
        call_id = None
        stream_sid = None

        user_pcm_buffer = io.BytesIO()
        agent_pcm_buffer = io.BytesIO()

        function_call_completed_time = None
        FUNCTION_CALL_GRACE_PERIOD = 5.0

        response_active = False

        _tool_call_received_at = None
        _tool_func_name = None
        _tool_response_sent_at = None
        _first_audio_after_tool = True

        async def receive_from_browser():
            nonlocal session_initialized, call_id, stream_sid
            try:
                async for msg in websocket.iter_text():
                    try:
                        data = json.loads(msg)

                        if data.get("event") == "start":
                            token = data["start"]["customParameters"].get("token")
                            if not token:
                                print("❌ No token provided in WebSocket connection")
                                await websocket.close(code=1008, reason="Authentication required")
                                return

                            try:
                                user_data = verify_jwt_token(token)
                                print(f"✅ WebSocket authenticated for user: {user_data['username']}")
                            except HTTPException as e:
                                print(f"❌ Invalid token in WebSocket: {e.detail}")
                                await websocket.close(code=1008, reason="Invalid or expired token")
                                return

                            call_id = data["start"]["customParameters"].get("call_id")
                            stream_sid = data["start"].get("streamSid", "browser-stream")
                            meta = call_metadata.get(call_id, {})
                            await initialize_session(openai_ws, call_id)
                            await send_initial_conversation_item(openai_ws)
                            session_initialized = True
                            continue

                        if data.get("event") == "media" and session_initialized:
                            payload_b64 = data["media"]["payload"]
                            pcm_bytes = base64.b64decode(payload_b64)
                            user_pcm_buffer.write(pcm_bytes)

                            mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
                            audio_append = {
                                "type": "input_audio_buffer.append",
                                "audio": base64.b64encode(mulaw_bytes).decode('utf-8')
                            }
                            await openai_ws.send(json.dumps(audio_append))

                        if data.get("event") == "stop":
                            print(f"🛑 Browser sent stop event for call {call_id}")
                            break

                    except json.JSONDecodeError as je:
                        print(f"⚠️ Failed to parse browser message: {je}")
                        continue
                    except Exception as inner_e:
                        print(f"⚠️ Error processing browser message: {inner_e}")
                        traceback.print_exc()
                        continue

                print(f"🔚 Browser WebSocket stream ended normally for call {call_id}")

            except WebSocketDisconnect:
                print(f"🔌 Browser WebSocket disconnected for call {call_id}")
            except Exception as e:
                print(f"❌ Unexpected error in browser receive loop: {e}")
                traceback.print_exc()

        current_rag_items = []

        async def receive_from_openai_and_forward():
            nonlocal function_call_completed_time, response_active, current_rag_items
            nonlocal _tool_call_received_at, _tool_func_name, _tool_response_sent_at, _first_audio_after_tool

            try:
                async for raw in openai_ws:
                    try:
                        response = json.loads(raw)
                        rtype = response.get("type")

                        if rtype not in ["response.audio.delta", "input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped"]:
                            print(f"📨 OpenAI event: {rtype}")

                        if rtype == 'error':
                            error_info = response.get('error', {})
                            error_type = error_info.get('type', 'unknown')
                            error_message = error_info.get('message', 'Unknown error')
                            error_code = error_info.get('code', '')

                            if error_code in ['item_delete_invalid_item_id', 'string_above_max_length']:
                                print(f"⚠️ OpenAI Error (non-critical) - Code: {error_code}, Message: {error_message}")
                                continue

                            print(f"❌ OpenAI Error - Type: {error_type}, Code: {error_code}, Message: {error_message}")

                            if error_code != 'response_cancel_not_active':
                                await websocket.send_json({
                                    "event": "error",
                                    "error_type": error_type,
                                    "message": error_message
                                })

                            if error_type in ['rate_limit_exceeded', 'server_error']:
                                print(f"⏳ Waiting 2 seconds before continuing after {error_type}...")
                                await asyncio.sleep(2)
                            continue

                        if rtype == 'rate_limits.updated':
                            rate_limits = response.get('rate_limits', [])
                            for limit in rate_limits:
                                remaining = limit.get('remaining', 0)
                                limit_name = limit.get('name', 'unknown')
                                if remaining < 10:
                                    print(f"⚠️ Rate limit warning: {limit_name} has {remaining} remaining")
                            continue

                        if rtype == 'response.created':
                            response_active = True
                            continue

                        if rtype == 'response.failed':
                            response_active = False
                            function_call_completed_time = None

                            resp_obj = response.get("response", {})
                            status_details = resp_obj.get("status_details", {})
                            error_info = status_details.get("error", {})
                            error_code = error_info.get("code", "")

                            if error_code == "rate_limit_exceeded":
                                print(f"⚠️ Rate limit hit - waiting 3 seconds before retry...")
                                await asyncio.sleep(3.0)
                                print("🔄 Retrying response after rate limit wait...")
                                await openai_ws.send(json.dumps({"type": "response.create"}))
                            else:
                                print(f"❌ Response failed: {error_info.get('message', 'Unknown error')}")
                                await asyncio.sleep(0.5)
                                await openai_ws.send(json.dumps({"type": "response.create"}))
                            continue

                        if rtype == 'response.cancelled':
                            print(f"ℹ️ Response was cancelled")
                            response_active = False
                            function_call_completed_time = None
                            continue

                        if rtype == 'input_audio_buffer.speech_started':
                            current_time = time.time()
                            if function_call_completed_time is not None:
                                time_since_function_call = current_time - function_call_completed_time
                                if time_since_function_call < FUNCTION_CALL_GRACE_PERIOD:
                                    print(f"⚠️ Ignoring interruption {time_since_function_call:.2f}s after function call (grace period: {FUNCTION_CALL_GRACE_PERIOD}s)")
                                    continue

                            await websocket.send_json({ "event": "clear" })
                            continue

                        if rtype == "response.done":
                            response_active = False
                            if _tool_call_received_at:
                                turn_total = (time.time() - _tool_call_received_at) * 1000
                                print(f"⏱️ [OPENAI TIMING] {_tool_func_name} | response_done total: {turn_total:.0f}ms")
                                _tool_call_received_at = None
                                _tool_response_sent_at = None
                            resp_obj = response.get("response", {})
                            resp_status = resp_obj.get("status", "unknown")
                            resp_status_details = resp_obj.get("status_details", {})
                            resp_output = resp_obj.get("output", [])
                            print(f"📋 Response done - Status: {resp_status}, Outputs: {len(resp_output)}, Details: {resp_status_details}")

                            usage = resp_obj.get("usage", {})
                            if usage:
                                input_tokens = usage.get("input_tokens", 0)
                                output_tokens = usage.get("output_tokens", 0)
                                total_tokens = usage.get("total_tokens", 0)
                                input_details = usage.get("input_token_details", {})
                                output_details = usage.get("output_token_details", {})
                                print(f"📊 Tokens — Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
                                if input_details:
                                    print(f"   Input breakdown  — text: {input_details.get('text_tokens', 0)}, audio: {input_details.get('audio_tokens', 0)}, cached: {input_details.get('cached_tokens', 0)}")
                                if output_details:
                                    print(f"   Output breakdown — text: {output_details.get('text_tokens', 0)}, audio: {output_details.get('audio_tokens', 0)}")

                            if resp_status != "completed":
                                print(f"⚠️ Response not completed normally: {resp_status}")
                                if resp_status_details:
                                    print(f"   Status details: {resp_status_details}")

                            if function_call_completed_time is not None:
                                print(f"✅ Response completed, clearing function call flag")
                                function_call_completed_time = None

                        if rtype == "response.content.done":
                            if function_call_completed_time is not None:
                                print(f"✅ Content completed, clearing function call flag")
                                function_call_completed_time = None

                        if rtype == "conversation.item.deleted":
                            deleted_item_id = response.get("item_id", "unknown")
                            if deleted_item_id.startswith("rag_"):
                                print(f"🗑️ Confirmed: RAG item {deleted_item_id} removed from context window")
                            continue

                        if rtype in LOG_EVENT_TYPES:
                            continue

                        if rtype == "response.audio.delta" and "delta" in response:
                            if function_call_completed_time is not None:
                                function_call_completed_time = None

                            if _tool_response_sent_at and _first_audio_after_tool:
                                _first_audio_after_tool = False
                                first_audio_delay = (time.time() - _tool_response_sent_at) * 1000
                                total_delay = (time.time() - _tool_call_received_at) * 1000
                                print(f"⏱️ [OPENAI TIMING] {_tool_func_name} | first_audio_after_tool_response: {first_audio_delay:.0f}ms | total_tool_to_audio: {total_delay:.0f}ms")

                            mulaw_b64 = response["delta"]
                            mulaw_bytes = base64.b64decode(mulaw_b64)

                            try:
                                pcm = audioop.ulaw2lin(mulaw_bytes, 2)
                            except Exception:
                                pcm = mulaw_bytes

                            agent_pcm_buffer.write(pcm)

                            pcm_b64 = base64.b64encode(pcm).decode('utf-8')

                            out = {
                                "event": "media",
                                "media": {
                                    "payload": pcm_b64,
                                    "format": "raw_pcm",
                                    "sampleRate": 8000,
                                    "channels": 1,
                                    "bitDepth": 16
                                }
                            }
                            await websocket.send_json(out)

                        elif rtype == "response.function_call_arguments.done":
                            func_name = response.get("name")
                            call_id_internal = response.get("call_id")
                            func_args_str = response.get("arguments", "{}")

                            try:
                                func_args = json.loads(func_args_str)
                            except json.JSONDecodeError:
                                func_args = {}

                            _tool_call_received_at = time.time()
                            _tool_func_name = func_name
                            _first_audio_after_tool = True

                            print(f"🔧 Function call: {func_name} with args: {func_args}")

                            exec_start = time.time()
                            try:
                                if func_name == "search_knowledge_base" and current_rag_items:
                                    print(f"🗑️ New RAG search requested - deleting {len(current_rag_items)} old RAG item(s) to make room...")
                                    for old_item_id in current_rag_items:
                                        delete_event = {
                                            "type": "conversation.item.delete",
                                            "item_id": old_item_id
                                        }
                                        try:
                                            await openai_ws.send(json.dumps(delete_event))
                                            print(f"   ✅ Deleted old RAG item: {old_item_id}")
                                        except Exception as del_err:
                                            print(f"   ⚠️ Failed to delete old RAG item {old_item_id}: {del_err}")
                                    current_rag_items.clear()

                                result = await asyncio.wait_for(
                                    execute_function_call(func_name, func_args),
                                    timeout=30.0
                                )
                            except asyncio.TimeoutError:
                                print(f"⚠️ Function call {func_name} timed out after 30 seconds")
                                result = {
                                    "success": False,
                                    "error": "timeout",
                                    "message": f"The operation timed out. Please try again."
                                }
                            exec_ms = (time.time() - exec_start) * 1000

                            print(f"✅ Function result: {result}")

                            rag_item_id = None
                            if func_name == "search_knowledge_base":
                                timestamp_ms = int(time.time() * 1000)
                                unique_str = f"{call_id_internal}_{timestamp_ms}"
                                hash_obj = hashlib.md5(unique_str.encode())
                                hash_hex = hash_obj.hexdigest()[:16]
                                rag_item_id = f"rag_{hash_hex}"
                                if len(rag_item_id) > 32:
                                    rag_item_id = rag_item_id[:32]

                            function_output = {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": call_id_internal,
                                    "output": json.dumps(result)
                                }
                            }
                            if rag_item_id:
                                function_output["item"]["id"] = rag_item_id
                                current_rag_items.append(rag_item_id)
                                print(f"📌 Tracking RAG item in context: {rag_item_id} (will persist until next RAG search)")

                            send_start = time.time()
                            await openai_ws.send(json.dumps(function_output))
                            await openai_ws.send(json.dumps({"type": "response.create"}))
                            _tool_response_sent_at = time.time()
                            send_ms = (_tool_response_sent_at - send_start) * 1000

                            function_call_completed_time = _tool_response_sent_at
                            print(f"⏱️ [OPENAI TIMING] {func_name} | exec: {exec_ms:.0f}ms | send_to_openai: {send_ms:.0f}ms | waiting for audio...")

                            outgoing_func_result = {
                                "event": "function_result",
                                "name": func_name,
                                "arguments": func_args_str,
                                "result": result
                            }
                            await websocket.send_json(outgoing_func_result)

                    except json.JSONDecodeError as je:
                        print(f"⚠️ Failed to parse OpenAI message: {je}")
                        continue
                    except Exception as inner_e:
                        print(f"⚠️ Error processing OpenAI message: {inner_e}")
                        continue

            except websockets.exceptions.ConnectionClosed as cc:
                print(f"❌ OpenAI WebSocket connection closed: code={cc.code}, reason={cc.reason}")
                try:
                    await websocket.send_json({
                        "event": "connection_error",
                        "message": "Connection to AI service was lost. Please refresh and try again."
                    })
                except:
                    pass
            except Exception as e:
                print(f"❌ Unexpected error in OpenAI receive loop: {e}")
                traceback.print_exc()
                try:
                    await websocket.send_json({
                        "event": "error",
                        "message": "An unexpected error occurred. Please try again."
                    })
                except:
                    pass

        recv_task = asyncio.create_task(receive_from_browser())
        send_task = asyncio.create_task(receive_from_openai_and_forward())

        try:
            done, pending = await asyncio.wait(
                [recv_task, send_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                if task == recv_task:
                    print(f"🔚 Browser receive task completed for call {call_id}")
                elif task == send_task:
                    print(f"🔚 OpenAI send task completed for call {call_id}")

                if task.exception():
                    print(f"❌ Task exception: {task.exception()}")

            for task in pending:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

        except Exception as e:
            print(f"❌ Error in main task loop: {e}")
            traceback.print_exc()
        finally:
            print(f"💾 Saving recordings for call {call_id}...")

            user_file_path = f"recordings/user/{call_id}_user.wav"
            agent_file_path = f"recordings/agent/{call_id}_agent.wav"

            def save_wav_file(path: str, pcm_data: bytes):
                with wave.open(path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(8000)
                    wf.writeframes(pcm_data)

            save_wav_file(user_file_path, user_pcm_buffer.getvalue())
            save_wav_file(agent_file_path, agent_pcm_buffer.getvalue())

            print(f"✅ Saved user audio: {user_file_path}")
            print(f"✅ Saved agent audio: {agent_file_path}")

            try:
                user_transcript = await transcribe_audio(user_file_path)
            except Exception as e:
                print(f"⚠️ Could not transcribe user audio: {e}")
                user_transcript = ""

            try:
                agent_transcript = await transcribe_audio(agent_file_path)
            except Exception as e:
                print(f"⚠️ Could not transcribe agent audio: {e}")
                agent_transcript = ""

            transcripts_output = {
                "call_id": call_id,
                "user_transcript": user_transcript,
                "agent_transcript": agent_transcript
            }

            print(f"📝 Transcripts saved for call {call_id}")

            analysis_result = await analyze_call_with_llm(call_id, user_transcript, agent_transcript)
            print(f"📊 Call analysis complete: {analysis_result}")

            with open(f"recordings/{call_id}_transcript.json", "w", encoding="utf-8") as f:
                json.dump(transcripts_output, f, ensure_ascii=False, indent=2)

            await websocket.close()


async def send_initial_conversation_item(openai_ws):
    await openai_ws.send(json.dumps({"type": "response.create"}))

@app.get("/call-analysis/{call_id}")
async def get_call_analysis(call_id: str, request: Request):
    token = get_token_from_request(request)
    user_data = verify_jwt_token(token)

    analysis_file_path = f"recordings/analysis/{call_id}_analysis.json"

    if not os.path.exists(analysis_file_path):
        raise HTTPException(status_code=404, detail=f"Analysis not found for call_id: {call_id}")

    try:
        with open(analysis_file_path, "r", encoding="utf-8") as f:
            analysis_data = json.load(f)
        return analysis_data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error reading analysis file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis: {str(e)}")

async def initialize_session(openai_ws, call_id):
    meta = call_metadata.get(call_id, {})
    instructions = meta.get("instructions", "")
    caller = meta.get("phone", "")
    voice = meta.get("voice", "echo")
    temperature = meta.get("temperature", 0.8)
    speed = meta.get("speed", 1.05)

    SYSTEM_MESSAGE = build_system_message(
        instructions=instructions,
        caller=caller,
        voice=voice
    )

    print(f"🔧 Initializing session with voice: {voice}, temp: {temperature}, speed: {speed}x")

    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.7,
                "prefix_padding_ms": 500,
                "silence_duration_ms": 1000,
                "create_response": True,
                "interrupt_response": True,
            },
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": voice,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": temperature,
            "speed": speed,
            'tool_choice': 'auto',
            'tools': function_call_tools
        }
    }

    print(f"📤 Sending session update to OpenAI")
    await openai_ws.send(json.dumps(session_update))


@app.get("/available-voices")
async def get_available_voices(request: Request):
    token = get_token_from_request(request)
    user_data = verify_jwt_token(token)

    return {
        "voices": AVAILABLE_VOICES
    }


def create_jwt_token(username: str, full_name: str) -> str:
    now = dt.now(timezone.utc)
    payload = {
        "username": username,
        "full_name": full_name,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": now
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_token_from_request(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return auth_header.replace("Bearer ", "")


@app.post("/auth/login")
async def login(credentials: dict = Body(...)):
    username = credentials.get("username", "").strip()
    password = credentials.get("password", "")

    if username in USERS_DB:
        user = USERS_DB[username]
        if user["password"] == password:
            token = create_jwt_token(username, user["full_name"])

            return {
                "success": True,
                "message": "Login successful",
                "token": token,
                "user": {
                    "username": username,
                    "full_name": user["full_name"]
                }
            }

    raise HTTPException(status_code=401, detail="Invalid username or password")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
