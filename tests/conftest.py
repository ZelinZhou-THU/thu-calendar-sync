from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_session():
    with patch("requests.Session") as mock_cls:
        session = MagicMock()
        mock_cls.return_value = session
        yield session


@pytest.fixture
def mock_outlook_app():
    with patch("win32com.client.Dispatch") as mock_dispatch:
        outlook = MagicMock()
        mock_dispatch.return_value = outlook
        yield outlook
