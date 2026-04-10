from __future__ import annotations

import os
import tempfile
import unittest

from vibescore.security import analyze_security
from vibescore._types import FileInfo


def _make_file(d: str, name: str, content: str, language: str = "python") -> FileInfo:
    path = os.path.join(d, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    return FileInfo(path=name, language=language, lines=lines, size_bytes=len(content.encode()))


class TestVC301HardcodedSecret(unittest.TestCase):
    def test_api_key_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "config.py", 'api_key = "sk-abc123456789abcdef"\n')
            # Create .gitignore so VC307 doesn't fire
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC301", codes)

    def test_secret_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "app.py", 'SECRET = "mysupersecretvalue1234"\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC301", codes)

    def test_short_value_not_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "app.py", 'api_key = "short"\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            vc301 = [i for i in result.issues if i.code == "VC301"]
            self.assertEqual(len(vc301), 0)


class TestVC302AWSKey(unittest.TestCase):
    def test_aws_key_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "creds.py", 'key = "AKIAIOSFODNN7EXAMPLE"\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC302", codes)


class TestVC303SQLInjection(unittest.TestCase):
    def test_format_string_sql_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "db.py", 'cursor.execute("SELECT * FROM t WHERE id=%s" % user_id)\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC303", codes)


class TestVC304ShellInjection(unittest.TestCase):
    def test_os_system_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "run.py", 'os.system("rm -rf " + user_input)\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC304", codes)

    def test_subprocess_call_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "run.py", 'subprocess.call("ls " + path)\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC304", codes)


class TestVC305UnsafeDeserialize(unittest.TestCase):
    def test_pickle_load_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "load.py", 'data = pickle.load(f)\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC305", codes)

    def test_yaml_load_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "load.py", 'data = yaml.load(content)\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC305", codes)

    def test_yaml_safe_loader_ok(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "load.py", 'data = yaml.load(content, Loader=yaml.SafeLoader)\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            vc305 = [i for i in result.issues if i.code == "VC305"]
            self.assertEqual(len(vc305), 0)


class TestVC306EvalExec(unittest.TestCase):
    def test_eval_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "dyn.py", 'result = eval(user_input)\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC306", codes)

    def test_exec_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "dyn.py", 'exec(code_string)\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC306", codes)


class TestVC307NoGitignore(unittest.TestCase):
    def test_no_gitignore_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "app.py", "pass\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC307", codes)

    def test_with_gitignore_ok(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "app.py", "pass\n")
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            vc307 = [i for i in result.issues if i.code == "VC307"]
            self.assertEqual(len(vc307), 0)


class TestVC308DebugTrue(unittest.TestCase):
    def test_debug_true_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "settings.py", 'DEBUG = True\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC308", codes)


class TestVC309PrivateKeyFile(unittest.TestCase):
    def test_pem_file_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "cert.pem", "-----BEGIN PRIVATE KEY-----\n", language="unknown")
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC309", codes)

    def test_id_rsa_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "id_rsa", "ssh-rsa AAAA...\n", language="unknown")
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC309", codes)


class TestSecurityCleanCode(unittest.TestCase):
    def test_clean_code_high_score(self):
        with tempfile.TemporaryDirectory() as d:
            fi = _make_file(d, "app.py", "import os\npath = os.getenv('SECRET')\n")
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            self.assertGreaterEqual(result.score, 90)

    def test_test_files_excluded_from_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            fi = _make_file(d, os.path.join("tests", "test_auth.py"),
                            'api_key = "test_fake_key_123456789"\n')
            with open(os.path.join(d, ".gitignore"), "w") as f:
                f.write("*.pyc\n")
            result = analyze_security([fi], d)
            vc301 = [i for i in result.issues if i.code == "VC301"]
            self.assertEqual(len(vc301), 0)


if __name__ == "__main__":
    unittest.main()
