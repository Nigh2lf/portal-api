"""Importação XML em processo separado (``xml_import.services.spawn``)."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid

from xml_import.services import spawn
from xml_import.services.batches import start_batch_in_background
from xml_import.services.execution import start_in_background


def test_spawn_runs_manage_py_without_cron(mocker, settings):
    popen = mocker.patch.object(subprocess, "Popen")
    os.environ["RUN_CRON"] = "true"
    try:
        spawn.spawn_import_command("--window", "--origin", "cron")
    finally:
        os.environ.pop("RUN_CRON", None)
    (cmd,), kwargs = popen.call_args
    assert cmd[0] == sys.executable
    assert cmd[1].endswith("manage.py")
    assert cmd[2:] == ["import_xml", "--window", "--origin", "cron"]
    assert kwargs["env"]["RUN_CRON"] == "false"
    assert kwargs["cwd"] == str(settings.BASE_DIR)
    # Sessão própria (POSIX) ou grupo próprio (Windows): sobrevive à reciclagem do worker.
    assert kwargs.get("start_new_session") or kwargs.get("creationflags")


def test_batch_and_simulation_are_spawned(db, mocker, settings, django_capture_on_commit_callbacks):
    settings.XML_IMPORT_SUBPROCESS = True
    spawned = mocker.patch("xml_import.services.spawn.spawn_import_command")
    thread = mocker.patch("threading.Thread")
    batch_id, advertiser_id = uuid.uuid4(), uuid.uuid4()

    # O lote só é disparado depois do commit: o processo filho precisa enxergar a linha.
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        start_batch_in_background(batch_id)
        assert spawned.call_count == 0
    assert len(callbacks) == 1
    start_in_background(advertiser_id, simulate=True)

    assert spawned.call_args_list == [
        mocker.call("--batch", batch_id),
        mocker.call("--advertiser", advertiser_id, "--simulate"),
    ]
    thread.assert_not_called()


def test_thread_fallback_when_subprocess_disabled(db, mocker, settings):
    settings.XML_IMPORT_SUBPROCESS = False
    spawned = mocker.patch("xml_import.services.spawn.spawn_import_command")
    thread = mocker.patch("xml_import.services.batches.threading.Thread")

    start_batch_in_background(uuid.uuid4())

    spawned.assert_not_called()
    thread.assert_called_once()
    thread.return_value.start.assert_called_once()
