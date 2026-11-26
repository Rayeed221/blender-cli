"""viewer/index.html -> viewer/app.html: the same app as page content for publishing
(the host adds the document skeleton, charset and viewport meta)."""
import re, os
here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "viewer")
s = open(os.path.join(here, "index.html")).read()
s = re.sub(r"<!doctype html>\s*<html[^>]*>\s*<head>", "", s, flags=re.I)
s = re.sub(r'<meta charset="utf-8">\s*', "", s)
s = re.sub(r'<meta name="viewport"[^>]*>\s*', "", s)
s = s.replace("</head>\n<body>", "").replace("</body>\n</html>", "")
s = s.replace(":root { --ink:", ":root { color-scheme: dark; --ink:")
open(os.path.join(here, "app.html"), "w").write(s.strip() + "\n")
print("wrote viewer/app.html", len(s))
