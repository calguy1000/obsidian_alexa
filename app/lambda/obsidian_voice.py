# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import os
import re
import requests
import time
import json
import hashlib
import random
import string

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Validate OBSIDIAN_REST environment variable
obsidian_rest = os.getenv("OBSIDIAN_REST")
if not obsidian_rest or not re.match(r'^https?://', obsidian_rest):
    # log the error
    logger.error("The OBSIDIAN_REST environment variable must be a valid HTTP or HTTPS URI")
    # raise an exception with a generic message
    raise ValueError("Configuration error 1001")

# Validate OBSIDIAN_REST_APIKEY environment variable
obsidian_rest_apikey = os.getenv("OBSIDIAN_REST_APIKEY")
if not obsidian_rest_apikey or not re.match(r'^[A-Fa-f0-9]+$|^[A-Za-z0-9+/=]+$', obsidian_rest_apikey):
    # log the error
    logger.error("The OBSIDIAN_REST_APIKEY environment variable must be a valid API key")
    # raise an exception with a generic message
    raise ValueError("Configuration error 1002")

def generate_cache_filename(api_key):
    """Generate an obfuscated cache filename using the API key and a hash of the current filename and path."""
    current_file_path = os.path.abspath(__file__)
    hash_key = hashlib.sha256((api_key + current_file_path).encode()).hexdigest()
    return f"/tmp/{hash_key}.json"

TOKEN_CACHE_PATH = generate_cache_filename(obsidian_rest_apikey)
TOKEN_CACHE_EXPIRY = 3600  # 1 hour in seconds

def get_jwt_token(api_key, rest_url):
    """Send a PUT request to the Obsidian URL /auth method to get a JWT token."""
    headers = {
        'x-api-key': api_key
    }
    try:
        response = requests.put(f"{rest_url}/auth", headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 403:
            logger.error("Forbidden: Invalid API key")
            raise ValueError("Configuration error 1003: Forbidden")
        elif response.status_code == 404:
            logger.error("Not Found: The requested resource could not be found")
            raise ValueError("Configuration error 1004: Not Found")
        else:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
    except requests.exceptions.RequestException as err:
        logger.error(f"Error connecting to the service: {err}")
        raise ValueError("Configuration error 1005: Connection error")

    token = response.json().get('token')
    if not token:
        raise ValueError("No token found in the response")
    return token

def get_cached_jwt_token(api_key, rest_url):
    """Wrapper for get_jwt_token to cache the token in the /tmp directory for up to one hour."""
    try:
        # Check if the cache file exists and is not expired
        if os.path.exists(TOKEN_CACHE_PATH):
            with open(TOKEN_CACHE_PATH, 'r') as cache_file:
                cache_data = json.load(cache_file)
                if time.time() - cache_data['timestamp'] < TOKEN_CACHE_EXPIRY:
                    return cache_data['token']
    except Exception as e:
        logger.error(f"Error reading token cache: {e}")

    # If cache is expired or does not exist, get a new token
    token = get_jwt_token(api_key, rest_url)
    try:
        # Save the new token to the cache file
        with open(TOKEN_CACHE_PATH, 'w') as cache_file:
            json.dump({'token': token, 'timestamp': time.time()}, cache_file)
    except Exception as e:
        logger.error(f"Error writing token cache: {e}")

    return token

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        try:
            # Ensure there is a valid JWT token
            token = get_cached_jwt_token(obsidian_rest_apikey, obsidian_rest)
            speak_output = "Welcome. To add text to the daily note say: \"Add to Daily\". for help you can say or Help. Which would you like to try?"
        except Exception as e:
            logger.error(f"Error obtaining JWT token: {e}")
            speak_output = "Sorry, there was an error with the vault service. Please try again later."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("What would you like to do?")  # .ask() is used to keep the session open for the user to respond
                .response
        )


class AddDailyTextIntentHandler(AbstractRequestHandler):
    """Handler for Add Daily Text Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AddDailyTextIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # get the slot text
        slots = handler_input.request_envelope.request.intent.slots
        text = slots['text'].value
        ask_str = None

        if text is None:
            return (
                handler_input.response_builder
                    .speak("Sorry, I didn't catch that. Please try again.")
                    .ask("What would you like to add?")
                    .response
            )

        if len(text.encode('utf-8')) > 1024:
            return (
                handler_input.response_builder
                    .speak("The text is too long. Please provide shorter text.")
                    .ask("What would you like to add?")
                    .response
            )

        try:
            # Ensure there is a valid JWT token
            token = get_cached_jwt_token(obsidian_rest_apikey, obsidian_rest)
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            data = {"content": text, "withtime": True}

            response = requests.patch(f"{obsidian_rest}/api/vault/daily", headers=headers, json=data)
            response.raise_for_status()  # Raise an exception for HTTP errors
            speak_output = "Got it. I've added the text to your daily note."
            ask_str = "What else would you like to do next?"
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            speak_output = "Sorry, there was an error with the service. Please try again later."
        except Exception as e:
            logger.error(f"Error obtaining JWT token: {e}")
            speak_output = "Sorry, there was an error with the authentication service. Please try again later."
        
        res = handler_input.response_builder.speak(speak_output)
        if ask_str:
            res.ask(ask_str)
        return res.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say 'Add to Daily' to add text to your daily note. How can I assist you further?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
    

class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .should_end_session(True)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return (
            handler_input.response_builder
                .set_should_end_session(True)
                .response
        )

class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        # Capture the initial user input
        speak_output = f"Sorry, I had trouble doing what you asked.  Please try again.  Or you can ask for help."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # Capture the user's utterance
        speak_output = f"Sorry, I didn't understand that. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AddDailyTextIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
