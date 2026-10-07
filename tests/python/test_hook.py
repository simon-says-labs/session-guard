"""Tests for hooks/session_guard_hook.py. Run: python3 -m unittest discover -s tests/python

Every test uses its own temporary state directory and runs the hook as a subprocess,
exactly as Claude Code does. Sound is disabled.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "..", "hooks", "session_guard_hook.py")


class HookTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, event, raw=None):
        env = dict(os.environ, SESSION_GUARD_STATE=self.state, SESSION_GUARD_SOUND="off")
        result = subprocess.run([sys.executable, HOOK], input=raw if raw is not None else json.dumps(event),
                                text=True, capture_output=True, env=env, timeout=10)
        return result.returncode

    def status(self, session_id):
        path = os.path.join(self.state, "sessions", session_id + ".json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def transcript(self, entries):
        path = os.path.join(self.state, "transcript.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
        return path

    def sounded(self):
        path = os.path.join(self.state, "session-guard.log")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [line.split("\t")[1] for line in f if line.rstrip().endswith("sound=yes")]

    @staticmethod
    def tool_result(text):
        return {"type": "user", "timestamp": "2026-10-05T15:05:56Z",
                "message": {"content": [{"type": "tool_result", "content": text}]}}

    # --- status files -------------------------------------------------------------

    def test_stop_writes_done_with_title_and_first_line(self):
        t = self.transcript([{"type": "ai-title", "aiTitle": "Refactor billing"}])
        code = self.run_hook({"hook_event_name": "Stop", "session_id": "s1", "cwd": "/x/proj",
                              "transcript_path": t, "last_assistant_message": "## Done: deploy ran\nStatus"})
        s = self.status("s1")
        self.assertEqual(code, 0)
        self.assertEqual(s["reason"], "done")
        self.assertEqual(s["title"], "Refactor billing")
        self.assertEqual(s["text"], "Done: deploy ran")
        self.assertEqual(s["transcript_size"], os.path.getsize(t))
        self.assertEqual((s["cwd"], s["transcript_path"]), ("/x/proj", t))

    def test_custom_title_wins_over_ai_title(self):
        t = self.transcript([{"type": "ai-title", "aiTitle": "AI"}, {"type": "custom-title", "customTitle": "Mine"}])
        self.run_hook({"hook_event_name": "Stop", "session_id": "s2", "transcript_path": t})
        self.assertEqual(self.status("s2")["title"], "Mine")

    def test_title_falls_back_to_folder_name(self):
        self.run_hook({"hook_event_name": "Stop", "session_id": "s3", "cwd": "/work/my-repo"})
        self.assertEqual(self.status("s3")["title"], "my-repo")

    def test_ask_user_question_is_a_question(self):
        self.run_hook({"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion", "session_id": "s4",
                       "tool_input": {"questions": [{"question": "Option A or B?"}]}})
        s = self.status("s4")
        self.assertEqual((s["reason"], s["text"]), ("question", "Option A or B?"))

    def test_permission_prompt_is_an_approval(self):
        self.run_hook({"hook_event_name": "Notification", "notification_type": "permission_prompt",
                       "session_id": "s5", "message": "Claude needs your permission to use Bash"})
        self.assertEqual(self.status("s5")["reason"], "approval")

    def test_permission_prompt_after_question_keeps_the_question(self):
        self.run_hook({"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion", "session_id": "s6",
                       "tool_input": {"questions": [{"question": "Which way?"}]}})
        self.run_hook({"hook_event_name": "Notification", "notification_type": "permission_prompt",
                       "session_id": "s6", "message": "Claude needs your permission"})
        s = self.status("s6")
        self.assertEqual((s["reason"], s["text"]), ("question", "Which way?"))

    def test_second_event_within_dedup_window_still_updates_status(self):
        self.run_hook({"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion", "session_id": "s7",
                       "tool_input": {"questions": [{"question": "A or B?"}]}})
        first = self.status("s7")["time"]
        time.sleep(0.05)
        self.run_hook({"hook_event_name": "Stop", "session_id": "s7", "last_assistant_message": "A it is"})
        s = self.status("s7")
        self.assertEqual((s["reason"], s["text"]), ("done", "A it is"))
        self.assertGreater(s["time"], first)

    def test_other_notification_types_write_nothing(self):
        self.run_hook({"hook_event_name": "Notification", "notification_type": "auth_success", "session_id": "s8"})
        self.assertIsNone(self.status("s8"))

    def test_invalid_input_exits_zero(self):
        self.assertEqual(self.run_hook(None, raw="not json"), 0)

    def test_session_id_cannot_escape_the_state_directory(self):
        self.run_hook({"hook_event_name": "Stop", "session_id": "../../evil", "last_assistant_message": "x"})
        self.assertFalse(os.path.exists(os.path.join(self.state, "evil.json")))
        self.assertEqual(os.listdir(os.path.join(self.state, "sessions")), ["evil.json"])

    # --- not finished yet ---------------------------------------------------------

    def test_stop_with_running_background_task_is_working(self):
        t = self.transcript([self.tool_result("Command running in background with ID: bsf6u7nc5. Output is being written to: /x")])
        self.run_hook({"hook_event_name": "Stop", "session_id": "b1", "transcript_path": t})
        self.assertEqual(self.status("b1")["reason"], "working")

    def test_stop_after_background_task_completed_is_done(self):
        t = self.transcript([
            self.tool_result("Command running in background with ID: bsf6u7nc5. Output is being written to: /x"),
            {"type": "attachment", "content": "<task-notification> <task-id>bsf6u7nc5</task-id> <status>completed</status>"},
        ])
        self.run_hook({"hook_event_name": "Stop", "session_id": "b2", "transcript_path": t})
        self.assertEqual(self.status("b2")["reason"], "done")

    def test_stopped_background_task_counts_as_finished(self):
        t = self.transcript([
            self.tool_result("Command did not complete within its 120s timeout and was moved to the background (ID: blofz5gp9)."),
            self.tool_result('{"message":"Successfully stopped task: blofz5gp9 (cd x)"}'),
        ])
        self.run_hook({"hook_event_name": "Stop", "session_id": "b3", "transcript_path": t})
        self.assertEqual(self.status("b3")["reason"], "done")

    def test_scheduled_turn_is_not_reported(self):
        t = self.transcript([
            {"type": "user", "turnOrigin": "human", "message": {"content": "task"}},
            {"type": "user", "turnOrigin": "scheduled", "isMeta": True, "message": {"content": "refresh page"}},
        ])
        self.run_hook({"hook_event_name": "Stop", "session_id": "c1", "transcript_path": t})
        self.assertEqual(self.status("c1")["reason"], "scheduled")

    def test_typed_turn_after_scheduled_one_is_done(self):
        t = self.transcript([
            {"type": "user", "turnOrigin": "scheduled", "message": {"content": "x"}},
            {"type": "user", "turnOrigin": "human", "message": {"content": "what are these?"}},
        ])
        self.run_hook({"hook_event_name": "Stop", "session_id": "c2", "transcript_path": t})
        self.assertEqual(self.status("c2")["reason"], "done")

    # --- sound --------------------------------------------------------------------

    def test_sound_only_for_questions(self):
        t = self.transcript([{"type": "user", "turnOrigin": "human"}])
        self.run_hook({"hook_event_name": "Stop", "session_id": "a", "transcript_path": t, "last_assistant_message": "done"})
        self.run_hook({"hook_event_name": "Notification", "notification_type": "permission_prompt", "session_id": "b"})
        self.run_hook({"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion", "session_id": "c",
                       "tool_input": {"questions": [{"question": "A or B?"}]}})
        self.run_hook({"hook_event_name": "Notification", "notification_type": "elicitation_dialog", "session_id": "d"})
        self.assertEqual(self.sounded(), ["AskUserQuestion", "elicitation_dialog"])


class StateDirTest(unittest.TestCase):
    """The state directory: %LOCALAPPDATA% on Windows, ~/.local/state elsewhere."""

    def load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("hook", HOOK)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_windows_uses_localappdata(self):
        hook = self.load()
        self.assertEqual(hook.default_state_dir("win32", {"LOCALAPPDATA": r"C:\Users\me\AppData\Local"}, "/home/me"),
                         os.path.join(r"C:\Users\me\AppData\Local", "session-guard"))

    def test_windows_without_localappdata_falls_back_to_home(self):
        hook = self.load()
        self.assertEqual(hook.default_state_dir("win32", {}, "/home/me"),
                         os.path.join("/home/me", ".local", "state", "session-guard"))

    def test_macos_and_linux_use_local_state(self):
        hook = self.load()
        for platform in ("darwin", "linux"):
            self.assertEqual(hook.default_state_dir(platform, {"LOCALAPPDATA": "x"}, "/home/me"),
                             os.path.join("/home/me", ".local", "state", "session-guard"))

    def test_sound_command_per_platform(self):
        hook = self.load()
        self.assertEqual(hook.sound_backend("win32"), "winsound")
        self.assertEqual(hook.sound_backend("darwin"), "afplay")
        self.assertEqual(hook.sound_backend("linux"), "paplay")
        self.assertIsNone(hook.sound_backend("aix"))


if __name__ == "__main__":
    unittest.main()
