import json
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession, ClientResponse

import pykoplenti
from pykoplenti import ApiClient

def test_process_parsing_v2():
    # V2 ProcessData often lacks 'unit'
    raw_response = """\
    {
        "id": "Inverter:State",
        "value": 6
    }"""
    process_data = pykoplenti.ProcessData(**json.loads(raw_response))
    assert process_data.id == "Inverter:State"
    assert process_data.unit is None
    assert process_data.value == 6

def test_settings_parsing_v2():
    # V2 SettingsData has object 'type' and 'access'
    raw_response = """\
    {
        "min": "0",
        "default": null,
        "access": {"type": "object", "description": "Access to the setting"},
        "unit": null,
        "id": "Properties:PowerId",
        "type": {"type": "object", "description": "The settings type"},
        "max": "100000"
    }"""
    settings_data = pykoplenti.SettingsData(**json.loads(raw_response))
    assert settings_data.id == "Properties:PowerId"
    assert isinstance(settings_data.type, dict)
    assert isinstance(settings_data.access, dict)

@pytest.mark.asyncio
async def test_login_autosensing_v2(websession: MagicMock):
    # Mock info/version -> 200 OK (V2 detected)
    websession.get.return_value.__aenter__.return_value = MagicMock(status=200)

    client = ApiClient(websession, "localhost")
    client._login = AsyncMock()

    await client.login("password")

    assert client._api_version == "v2"
    client._login.assert_awaited()

    # Verify autosensing call
    websession.get.assert_called_with(ANY, timeout=ANY)
    args, _ = websession.get.call_args
    assert "/api/v2/info/version" in str(args[0])

@pytest.mark.asyncio
async def test_login_autosensing_v1(websession: MagicMock):
    # Mock info/version -> 404 (V2 not found)
    websession.get.return_value.__aenter__.return_value = MagicMock(status=404)

    client = ApiClient(websession, "localhost")
    client._login = AsyncMock()

    await client.login("password")

    assert client._api_version == "v1"

@pytest.mark.asyncio
async def test_session_request_v2_header(websession: MagicMock):
    client = ApiClient(websession, "localhost")
    client._api_version = "v2"
    client._token = "my_jwt_token"

    # Mock response
    response = MagicMock(status=200, json=AsyncMock(return_value=[
         {"moduleid": "module", "processdata": [{"id": "data", "value": 0}]}
    ]))
    websession.request.return_value.__aenter__.side_effect = [response]

    await client.get_process_data_values("module", "data")

    # Check headers
    # The last call should be the request to processdata
    args, kwargs = websession.request.call_args

    assert kwargs["headers"]["authorization"] == "Bearer my_jwt_token"
    assert "/api/v2/" in str(args[1])

@pytest.mark.asyncio
async def test_session_request_v1_header(websession: MagicMock):
    client = ApiClient(websession, "localhost")
    client._api_version = "v1"
    client.session_id = "my_session_id"

    # Mock response
    response = MagicMock(status=200, json=AsyncMock(return_value=[
        {"moduleid": "module", "processdata": [{"id": "data", "value": 0}]}
    ]))
    websession.request.return_value.__aenter__.side_effect = [response]

    await client.get_process_data_values("module", "data")

    # Check headers
    args, kwargs = websession.request.call_args

    assert kwargs["headers"]["authorization"] == "Session my_session_id"
    assert "/api/v1/" in str(args[1])
