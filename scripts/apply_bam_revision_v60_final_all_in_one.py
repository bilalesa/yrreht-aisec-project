#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

VERSION = "2.2.6"
BRANCH = "bam-banking-ui"
IMAGE = "bambank-demo:v60"
CONTAINER = "bambank-demo-v60"
PORT = "8081"

V60_JS = base64.b64decode('LyogQkFNX0JBTktfVUlfUkVWSVNJT05fVjYwICovCigoKSA9PiB7CiAgaWYgKHdpbmRvdy5fX2JhbVJldmlzaW9uVjYwKSByZXR1cm47CiAgd2luZG93Ll9fYmFtUmV2aXNpb25WNjAgPSB0cnVlOwoKICBjb25zdCBxID0gKHNlbGVjdG9yLCByb290ID0gZG9jdW1lbnQpID0+IHJvb3QucXVlcnlTZWxlY3RvcihzZWxlY3Rvcik7CiAgY29uc3QgcWEgPSAoc2VsZWN0b3IsIHJvb3QgPSBkb2N1bWVudCkgPT4gWy4uLnJvb3QucXVlcnlTZWxlY3RvckFsbChzZWxlY3RvcildOwoKICBjb25zdCBjaGF0SWNvbiA9IGAKICAgIDxzdmcgY2xhc3M9ImJhbS1jaGF0LWljb24tdjYwIiB2aWV3Qm94PSIwIDAgNDggNDgiCiAgICAgICAgIGZvY3VzYWJsZT0iZmFsc2UiIGFyaWEtaGlkZGVuPSJ0cnVlIj4KICAgICAgPHBhdGggY2xhc3M9ImJhbS1jaGF0LXNoZWxsLXY2MCIKICAgICAgICBkPSJNOS41IDkuNWgyOWE1IDUgMCAwIDEgNSA1djE2YTUgNSAwIDAgMS01IDVIMjNsLTEwLjUgNnYtNi40YTUgNSAwIDAgMS00LTQuOVYxNC41YTUgNSAwIDAgMSA1LTVaIi8+CiAgICAgIDxjaXJjbGUgY2xhc3M9ImJhbS1jaGF0LWRvdC12NjAgZG90LTEiIGN4PSIxOCIgY3k9IjIzIiByPSIyLjIiLz4KICAgICAgPGNpcmNsZSBjbGFzcz0iYmFtLWNoYXQtZG90LXY2MCBkb3QtMiIgY3g9IjI0LjUiIGN5PSIyMyIgcj0iMi4yIi8+CiAgICAgIDxjaXJjbGUgY2xhc3M9ImJhbS1jaGF0LWRvdC12NjAgZG90LTMiIGN4PSIzMSIgY3k9IjIzIiByPSIyLjIiLz4KICAgICAgPHBhdGggY2xhc3M9ImJhbS1jaGF0LXNwYXJrLXY2MCIKICAgICAgICBkPSJNMzcgNC44Yy40NSAyLjc1IDIuMDUgNC4zNSA0LjggNC44LTIuNzUuNDUtNC4zNSAyLjA1LTQuOCA0LjgtLjQ1LTIuNzUtMi4wNS00LjM1LTQuOC00LjggMi43NS0uNDUgNC4zNS0yLjA1IDQuOC00LjhaIi8+CiAgICA8L3N2Zz5gOwoKICBjb25zdCBndWFyZEljb24gPSBgCiAgICA8c3BhbiBjbGFzcz0iYmFtLWd1YXJkLWljb24tdjYwIiBhcmlhLWhpZGRlbj0idHJ1ZSI+CiAgICAgIDxzdmcgdmlld0JveD0iMCAwIDI0IDI0Ij4KICAgICAgICA8cGF0aCBkPSJNMTIgMy4yIDE5IDZ2NS4yYzAgNC41LTIuOCA3LjctNyA5LjMtNC4yLTEuNi03LTQuOC03LTkuM1Y2bDctMi44WiI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Im04LjggMTIgMi4xIDIuMSA0LjUtNC43Ij48L3BhdGg+CiAgICAgIDwvc3ZnPgogICAgPC9zcGFuPmA7CgogIGZ1bmN0aW9uIGN1cnJlbnRMYW5ndWFnZSgpIHsKICAgIHJldHVybiAoCiAgICAgIGxvY2FsU3RvcmFnZS5nZXRJdGVtKCdiYW0tbGFuZ3VhZ2UnKSA9PT0gJ2lkJyB8fAogICAgICBkb2N1bWVudC5kb2N1bWVudEVsZW1lbnQubGFuZyA9PT0gJ2lkJwogICAgKSA/ICdpZCcgOiAnZW4nOwogIH0KCiAgZnVuY3Rpb24gbGF1bmNoZXJDb3B5KCkgewogICAgcmV0dXJuIGN1cnJlbnRMYW5ndWFnZSgpID09PSAnaWQnCiAgICAgID8gewogICAgICAgICAgdGl0bGU6ICdCQU0gQXNzaXN0JywKICAgICAgICAgIG1ldGE6ICdCYW50dWFuIEFJICYga2VhbWFuYW4nLAogICAgICAgICAgb3BlbjogJ0J1a2EgQkFNIEFzc2lzdCcKICAgICAgICB9CiAgICAgIDogewogICAgICAgICAgdGl0bGU6ICdCQU0gQXNzaXN0JywKICAgICAgICAgIG1ldGE6ICdBSSBoZWxwICYgc2VjdXJpdHknLAogICAgICAgICAgb3BlbjogJ09wZW4gQkFNIEFzc2lzdCcKICAgICAgICB9OwogIH0KCiAgZnVuY3Rpb24gZGVjb3JhdGVBc3Npc3RMYXVuY2hlcigpIHsKICAgIGNvbnN0IGxhdW5jaGVyID0gcSgnI2JhbS1hc3Npc3QtbGF1bmNoZXInKTsKICAgIGlmICghbGF1bmNoZXIpIHJldHVybiBmYWxzZTsKCiAgICBjb25zdCBjb3B5ID0gbGF1bmNoZXJDb3B5KCk7CgogICAgbGF1bmNoZXIuY2xhc3NMaXN0LmFkZCgnYmFtLWFzc2lzdC1sYXVuY2hlci12NjAnKTsKICAgIGxhdW5jaGVyLnNldEF0dHJpYnV0ZSgnYXJpYS1sYWJlbCcsIGNvcHkub3Blbik7CiAgICBsYXVuY2hlci5zZXRBdHRyaWJ1dGUoJ3RpdGxlJywgY29weS5vcGVuKTsKCiAgICBpZiAobGF1bmNoZXIuZGF0YXNldC5iYW1MYXVuY2hlclY2MCAhPT0gJ3RydWUnKSB7CiAgICAgIGxhdW5jaGVyLmRhdGFzZXQuYmFtTGF1bmNoZXJWNjAgPSAndHJ1ZSc7CiAgICAgIGxhdW5jaGVyLmlubmVySFRNTCA9IGAKICAgICAgICA8c3BhbiBjbGFzcz0iYmFtLWFzc2lzdC1sYXVuY2hlci1tYXJrLXY2MCI+CiAgICAgICAgICAke2NoYXRJY29ufQogICAgICAgIDwvc3Bhbj4KICAgICAgICA8c3BhbiBjbGFzcz0iYmFtLWFzc2lzdC1sYXVuY2hlci1jb3B5LXY2MCI+CiAgICAgICAgICA8c3Ryb25nIGlkPSJiYW0tYXNzaXN0LWxhdW5jaGVyLXRpdGxlIj4ke2NvcHkudGl0bGV9PC9zdHJvbmc+CiAgICAgICAgICA8c21hbGwgaWQ9ImJhbS1hc3Npc3QtbGF1bmNoZXItbWV0YSI+JHtjb3B5Lm1ldGF9PC9zbWFsbD4KICAgICAgICA8L3NwYW4+CiAgICAgICAgPHNwYW4gY2xhc3M9ImJhbS1hc3Npc3QtcHJlc2VuY2UtdjYwIiBhcmlhLWhpZGRlbj0idHJ1ZSI+CiAgICAgICAgICA8aT48L2k+T25saW5lCiAgICAgICAgPC9zcGFuPgogICAgICAgIDxzdmcgY2xhc3M9ImJhbS1hc3Npc3QtY2hldnJvbi12NjAiIHZpZXdCb3g9IjAgMCAyNCAyNCIKICAgICAgICAgICAgIGFyaWEtaGlkZGVuPSJ0cnVlIj4KICAgICAgICAgIDxwYXRoIGQ9Im04IDEwIDQgNCA0LTQiPjwvcGF0aD4KICAgICAgICA8L3N2Zz5gOwogICAgfQoKICAgIGNvbnN0IHRpdGxlID0gcSgnI2JhbS1hc3Npc3QtbGF1bmNoZXItdGl0bGUnLCBsYXVuY2hlcik7CiAgICBjb25zdCBtZXRhID0gcSgnI2JhbS1hc3Npc3QtbGF1bmNoZXItbWV0YScsIGxhdW5jaGVyKTsKICAgIGlmICh0aXRsZSkgdGl0bGUudGV4dENvbnRlbnQgPSBjb3B5LnRpdGxlOwogICAgaWYgKG1ldGEpIG1ldGEudGV4dENvbnRlbnQgPSBjb3B5Lm1ldGE7CgogICAgY29uc3QgcGFuZWxNYXJrID0gcSgnI2JhbS1hc3Npc3QtcGFuZWwgLmJhbS1hc3Npc3QtcGFuZWwtbWFyaycpOwogICAgaWYgKHBhbmVsTWFyaykgewogICAgICBwYW5lbE1hcmsuY2xhc3NMaXN0LmFkZCgnYmFtLWFzc2lzdC1wYW5lbC1tYXJrLXY2MCcpOwogICAgICBwYW5lbE1hcmsuaW5uZXJIVE1MID0gY2hhdEljb247CiAgICB9CgogICAgY29uc3QgY2hhdEF2YXRhciA9IHEoJyNjaGF0LXBhbmVsIC5hc3Npc3RhbnQtYXZhdGFyJyk7CiAgICBpZiAoY2hhdEF2YXRhcikgewogICAgICBjaGF0QXZhdGFyLmNsYXNzTGlzdC5hZGQoJ2JhbS1jaGF0LWF2YXRhci12NjAnKTsKICAgICAgY2hhdEF2YXRhci5pbm5lckhUTUwgPSBjaGF0SWNvbjsKICAgIH0KCiAgICByZXR1cm4gdHJ1ZTsKICB9CgogIGZ1bmN0aW9uIGd1YXJkVGV4dFdyYXBwZXIoY29udGVudCkgewogICAgbGV0IHdyYXBwZXIgPSBxKCcuYmFtLWd1YXJkLXRleHQtdjYwJywgY29udGVudCk7CiAgICBpZiAod3JhcHBlcikgcmV0dXJuIHdyYXBwZXI7CgogICAgd3JhcHBlciA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ3NwYW4nKTsKICAgIHdyYXBwZXIuY2xhc3NOYW1lID0gJ2JhbS1ndWFyZC10ZXh0LXY2MCc7CgogICAgY29uc3QgdGl0bGUgPSBxYSgKICAgICAgJzpzY29wZSA+IHN0cm9uZyw6c2NvcGUgPiBoMiw6c2NvcGUgPiBoMyw6c2NvcGUgPiBoNCcsCiAgICAgIGNvbnRlbnQKICAgICkuZmluZChub2RlID0+IG5vZGUudGV4dENvbnRlbnQudHJpbSgpID09PSAnQUkgR3VhcmQnKTsKCiAgICBjb25zdCBkZXRhaWwgPSBxKCc6c2NvcGUgPiBzbWFsbCw6c2NvcGUgPiBwJywgY29udGVudCk7CgogICAgaWYgKHRpdGxlKSB3cmFwcGVyLmFwcGVuZENoaWxkKHRpdGxlKTsKICAgIGlmIChkZXRhaWwpIHdyYXBwZXIuYXBwZW5kQ2hpbGQoZGV0YWlsKTsKICAgIGNvbnRlbnQuYXBwZW5kQ2hpbGQod3JhcHBlcik7CiAgICByZXR1cm4gd3JhcHBlcjsKICB9CgogIGZ1bmN0aW9uIHJlbmRlckd1YXJkU3RhdGUoKSB7CiAgICBjb25zdCB0b2dnbGUgPSBxKCcjZ3VhcmQtdG9nZ2xlJyk7CiAgICBjb25zdCByb3cgPSBxKCcjY2hhdC1wYW5lbCAuZ3VhcmQtYmFubmVyJyk7CiAgICBpZiAoIXRvZ2dsZSB8fCAhcm93KSByZXR1cm4gZmFsc2U7CgogICAgY29uc3QgZW5hYmxlZCA9IEJvb2xlYW4odG9nZ2xlLmNoZWNrZWQpOwogICAgcm93LmNsYXNzTGlzdC50b2dnbGUoJ2lzLWVuYWJsZWQtdjYwJywgZW5hYmxlZCk7CgogICAgY29uc3QgbGFiZWwgPSBxKCcjZ3VhcmQtbW9kZS1sYWJlbCcpOwogICAgaWYgKGxhYmVsKSB7CiAgICAgIGxhYmVsLnRleHRDb250ZW50ID0gZW5hYmxlZAogICAgICAgID8gJ1Byb3RlY3RlZCDCtyBwcm9tcHRzIGFuZCByZXNwb25zZXMgaW5zcGVjdGVkJwogICAgICAgIDogJ1VucHJvdGVjdGVkIGRlbW8gwrcgZGlyZWN0IG1vZGVsIHJlc3BvbnNlJzsKICAgIH0KCiAgICByZXR1cm4gdHJ1ZTsKICB9CgogIGZ1bmN0aW9uIGluc3RhbGxHdWFyZENvbnRyb2woKSB7CiAgICBjb25zdCB0b2dnbGUgPSBxKCcjZ3VhcmQtdG9nZ2xlJyk7CiAgICBjb25zdCByb3cgPSBxKCcjY2hhdC1wYW5lbCAuZ3VhcmQtYmFubmVyJyk7CiAgICBpZiAoIXRvZ2dsZSB8fCAhcm93KSByZXR1cm4gZmFsc2U7CgogICAgLyoKICAgICAqIE9ubHkgI2d1YXJkLXRvZ2dsZSBiZWxvbmdzIHRvIEFJIEd1YXJkLgogICAgICogWlRTQSBpcyBhbiBpbmRlcGVuZGVudCBjb250cm9sLgogICAgICovCiAgICB0b2dnbGUuZGlzYWJsZWQgPSBmYWxzZTsKICAgIHRvZ2dsZS5yZW1vdmVBdHRyaWJ1dGUoJ2Rpc2FibGVkJyk7CiAgICB0b2dnbGUuc2V0QXR0cmlidXRlKCdhcmlhLWRpc2FibGVkJywgJ2ZhbHNlJyk7CgogICAgcm93LmNsYXNzTGlzdC5yZW1vdmUoCiAgICAgICdiYW0tZ3VhcmQtcm93LXY1OCcsCiAgICAgICdiYW0tcnVudGltZS1jb250cm9sLXY1NScKICAgICk7CiAgICByb3cuY2xhc3NMaXN0LmFkZCgnYmFtLWd1YXJkLXJvdy12NjAnKTsKCiAgICBxYSgnLmJhbS1ydW50aW1lLWljb24tdjU1LC5iYW0tZ3VhcmQtaWNvbi12NTgnLCByb3cpCiAgICAgIC5mb3JFYWNoKG5vZGUgPT4gbm9kZS5yZW1vdmUoKSk7CgogICAgY29uc3QgY29udGVudCA9IHEoJzpzY29wZSA+IGRpdicsIHJvdyk7CiAgICBpZiAoY29udGVudCkgewogICAgICBjb250ZW50LmNsYXNzTGlzdC5yZW1vdmUoJ2JhbS1ndWFyZC1jb3B5LXY1OCcpOwogICAgICBjb250ZW50LmNsYXNzTGlzdC5hZGQoJ2JhbS1ndWFyZC1jb3B5LXY2MCcpOwoKICAgICAgaWYgKCFxKCcuYmFtLWd1YXJkLWljb24tdjYwJywgY29udGVudCkpIHsKICAgICAgICBjb250ZW50Lmluc2VydEFkamFjZW50SFRNTCgnYWZ0ZXJiZWdpbicsIGd1YXJkSWNvbik7CiAgICAgIH0KCiAgICAgIGd1YXJkVGV4dFdyYXBwZXIoY29udGVudCk7CiAgICB9CgogICAgaWYgKHRvZ2dsZS5kYXRhc2V0LmJhbUd1YXJkVjYwICE9PSAndHJ1ZScpIHsKICAgICAgdG9nZ2xlLmRhdGFzZXQuYmFtR3VhcmRWNjAgPSAndHJ1ZSc7CiAgICAgIGxldCB6dHNhQmVmb3JlID0gbnVsbDsKCiAgICAgIHRvZ2dsZS5hZGRFdmVudExpc3RlbmVyKCdwb2ludGVyZG93bicsICgpID0+IHsKICAgICAgICBjb25zdCB6dHNhID0gcSgnI3p0c2EtdG9nZ2xlLXYzMCcpOwogICAgICAgIHp0c2FCZWZvcmUgPSB6dHNhID8gQm9vbGVhbih6dHNhLmNoZWNrZWQpIDogbnVsbDsKICAgICAgfSwgdHJ1ZSk7CgogICAgICB0b2dnbGUuYWRkRXZlbnRMaXN0ZW5lcignY2hhbmdlJywgKCkgPT4gewogICAgICAgIGNvbnN0IHp0c2EgPSBxKCcjenRzYS10b2dnbGUtdjMwJyk7CgogICAgICAgIGlmICgKICAgICAgICAgIHp0c2EgJiYKICAgICAgICAgIHp0c2FCZWZvcmUgIT09IG51bGwgJiYKICAgICAgICAgIHp0c2EuY2hlY2tlZCAhPT0genRzYUJlZm9yZQogICAgICAgICkgewogICAgICAgICAgenRzYS5jaGVja2VkID0genRzYUJlZm9yZTsKICAgICAgICAgIGxvY2FsU3RvcmFnZS5zZXRJdGVtKAogICAgICAgICAgICAnYmFtLXp0c2EtbW9jay1lbmFibGVkJywKICAgICAgICAgICAgU3RyaW5nKHp0c2FCZWZvcmUpCiAgICAgICAgICApOwogICAgICAgICAgenRzYS5kaXNwYXRjaEV2ZW50KG5ldyBFdmVudCgnY2hhbmdlJywgeyBidWJibGVzOiB0cnVlIH0pKTsKICAgICAgICB9CgogICAgICAgIGlmICh0eXBlb2Ygc3RhdGUgPT09ICdvYmplY3QnICYmIHN0YXRlKSB7CiAgICAgICAgICBzdGF0ZS5ndWFyZEVuYWJsZWQgPSBCb29sZWFuKHRvZ2dsZS5jaGVja2VkKTsKICAgICAgICB9CgogICAgICAgIHJlbmRlckd1YXJkU3RhdGUoKTsKICAgICAgfSk7CiAgICB9CgogICAgcmVuZGVyR3VhcmRTdGF0ZSgpOwogICAgcmV0dXJuIHRydWU7CiAgfQoKICBmdW5jdGlvbiByZW1vdmVGaWxlU2VjdXJpdHlSZWFkeSgpIHsKICAgIFsKICAgICAgJy5iYW0tZmlsZS1zZWN1cml0eS1iYWRnZS12MjcnLAogICAgICAnLmZpbGUtc2VjdXJpdHktYmFkZ2UnLAogICAgICAnLmZpbGUtc2VjdXJpdHktcmVhZHknLAogICAgICAnLmJhbS1maWxlLXByb3RlY3Rpb24tc3RhdHVzJywKICAgICAgJ1tkYXRhLWZpbGUtc2VjdXJpdHktcmVhZHldJwogICAgXS5mb3JFYWNoKHNlbGVjdG9yID0+IHsKICAgICAgcWEoc2VsZWN0b3IpLmZvckVhY2gobm9kZSA9PiBub2RlLnJlbW92ZSgpKTsKICAgIH0pOwoKICAgIGNvbnN0IHBheUJpbGxzID0gcSgKICAgICAgJyNkYXNoYm9hcmQtcGFnZSAucXVpY2stYWN0aW9ucyA+IGJ1dHRvbltkYXRhLW9wZW49ImZpbGUiXScKICAgICk7CgogICAgaWYgKHBheUJpbGxzKSB7CiAgICAgIHFhKCdlbSxiLHNtYWxsLHNwYW4nLCBwYXlCaWxscykuZm9yRWFjaChub2RlID0+IHsKICAgICAgICBpZiAobm9kZS5jbGFzc0xpc3QuY29udGFpbnMoJ2JhbS1maWxlLXNlY3VyaXR5LXNoaWVsZC12MjgnKSkgewogICAgICAgICAgcmV0dXJuOwogICAgICAgIH0KCiAgICAgICAgY29uc3QgdGV4dCA9IChub2RlLnRleHRDb250ZW50IHx8ICcnKQogICAgICAgICAgLnJlcGxhY2UoL1xzKy9nLCAnICcpCiAgICAgICAgICAudHJpbSgpCiAgICAgICAgICAudG9Mb3dlckNhc2UoKTsKCiAgICAgICAgaWYgKAogICAgICAgICAgdGV4dCA9PT0gJ2ZpbGUgc2VjdXJpdHkgcmVhZHknIHx8CiAgICAgICAgICB0ZXh0ID09PSAnZmlsZSBzZWN1cml0eSBwcm90ZWN0ZWQnIHx8CiAgICAgICAgICB0ZXh0ID09PSAncHJvdGVjdGVkIGJ5IGZpbGUgc2VjdXJpdHknIHx8CiAgICAgICAgICB0ZXh0ID09PSAnZGlsaW5kdW5naSBmaWxlIHNlY3VyaXR5JwogICAgICAgICkgewogICAgICAgICAgbm9kZS5yZW1vdmUoKTsKICAgICAgICB9CiAgICAgIH0pOwogICAgfQogIH0KCiAgZnVuY3Rpb24gaW5zdGFsbCgpIHsKICAgIGRlY29yYXRlQXNzaXN0TGF1bmNoZXIoKTsKICAgIGluc3RhbGxHdWFyZENvbnRyb2woKTsKICAgIHJlbW92ZUZpbGVTZWN1cml0eVJlYWR5KCk7CgogICAgY29uc3QgZm9ybSA9IHEoJyNjaGF0LWZvcm0nKTsKICAgIGlmIChmb3JtKSBmb3JtLm5vVmFsaWRhdGUgPSB0cnVlOwogIH0KCiAgaW5zdGFsbCgpOwogIFsxMjAsIDM1MCwgODAwLCAxNTAwLCAyODAwXS5mb3JFYWNoKGRlbGF5ID0+IHsKICAgIHdpbmRvdy5zZXRUaW1lb3V0KGluc3RhbGwsIGRlbGF5KTsKICB9KTsKCiAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLCBldmVudCA9PiB7CiAgICBpZiAoCiAgICAgIGV2ZW50LnRhcmdldCBpbnN0YW5jZW9mIEVsZW1lbnQgJiYKICAgICAgZXZlbnQudGFyZ2V0LmNsb3Nlc3QoCiAgICAgICAgJyNiYW0tYXNzaXN0LWxhdW5jaGVyLCcgKwogICAgICAgICcjYmFtLWFzc2lzdC1jaGF0LCcgKwogICAgICAgICcjYmFtLWFzc2lzdC1ndWFyZCwnICsKICAgICAgICAnI2d1YXJkLXRvZ2dsZSwnICsKICAgICAgICAnW2RhdGEtb3Blbj0iZmlsZSJdJwogICAgICApCiAgICApIHsKICAgICAgd2luZG93LnNldFRpbWVvdXQoaW5zdGFsbCwgMCk7CiAgICAgIHdpbmRvdy5zZXRUaW1lb3V0KGluc3RhbGwsIDE4MCk7CiAgICB9CiAgfSwgdHJ1ZSk7CgogIFsnI2xhbmd1YWdlJywgJyNzZXR0aW5ncy1sYW5ndWFnZSddLmZvckVhY2goc2VsZWN0b3IgPT4gewogICAgcShzZWxlY3Rvcik/LmFkZEV2ZW50TGlzdGVuZXIoJ2NoYW5nZScsICgpID0+IHsKICAgICAgd2luZG93LnNldFRpbWVvdXQoaW5zdGFsbCwgMCk7CiAgICAgIHdpbmRvdy5zZXRUaW1lb3V0KGluc3RhbGwsIDE2MCk7CiAgICB9KTsKICB9KTsKfSkoKTsK').decode()
V60_CSS = base64.b64decode('LyogQkFNX0JBTktfVUlfUkVWSVNJT05fVjYwICovCgouYmFtLWZpbGUtc2VjdXJpdHktYmFkZ2UtdjI3LAouZmlsZS1zZWN1cml0eS1iYWRnZSwKLmZpbGUtc2VjdXJpdHktcmVhZHksCi5iYW0tZmlsZS1wcm90ZWN0aW9uLXN0YXR1cywKW2RhdGEtZmlsZS1zZWN1cml0eS1yZWFkeV0sCi5iYW0tZmlsZS1yZWFkeS1oaWRkZW4tdjU5LTEgewogIGRpc3BsYXk6IG5vbmUgIWltcG9ydGFudDsKICB2aXNpYmlsaXR5OiBoaWRkZW4gIWltcG9ydGFudDsKICBwb2ludGVyLWV2ZW50czogbm9uZSAhaW1wb3J0YW50Owp9CgovKiBBSSBHdWFyZDogY29tcGFjdCwgaG9yaXpvbnRhbCBhbmQgaW5kZXBlbmRlbnQgZnJvbSBaVFNBLiAqLwojY2hhdC1wYW5lbCAuZ3VhcmQtYmFubmVyLmJhbS1ndWFyZC1yb3ctdjYwIHsKICBtaW4taGVpZ2h0OiA5MnB4ICFpbXBvcnRhbnQ7CiAgZGlzcGxheTogZ3JpZCAhaW1wb3J0YW50OwogIGdyaWQtdGVtcGxhdGUtY29sdW1uczogbWlubWF4KDAsIDFmcikgYXV0byAhaW1wb3J0YW50OwogIGFsaWduLWl0ZW1zOiBjZW50ZXIgIWltcG9ydGFudDsKICBnYXA6IDE4cHggIWltcG9ydGFudDsKICBwYWRkaW5nOiAxNnB4IDIycHggIWltcG9ydGFudDsKfQoKI2NoYXQtcGFuZWwgLmd1YXJkLWJhbm5lci5iYW0tZ3VhcmQtcm93LXY2MCA+IC5iYW0tZ3VhcmQtY29weS12NjAgewogIG1pbi13aWR0aDogMDsKICBkaXNwbGF5OiBmbGV4ICFpbXBvcnRhbnQ7CiAgYWxpZ24taXRlbXM6IGNlbnRlciAhaW1wb3J0YW50OwogIGdhcDogMTRweCAhaW1wb3J0YW50Owp9CgouYmFtLWd1YXJkLWljb24tdjYwIHsKICB3aWR0aDogNDJweDsKICBoZWlnaHQ6IDQycHg7CiAgZGlzcGxheTogZ3JpZDsKICBwbGFjZS1pdGVtczogY2VudGVyOwogIGZsZXg6IDAgMCA0MnB4OwogIGJvcmRlcjogMXB4IHNvbGlkICNkNmUyZjM7CiAgYm9yZGVyLXJhZGl1czogMTNweDsKICBiYWNrZ3JvdW5kOiBsaW5lYXItZ3JhZGllbnQoMTQ1ZGVnLCAjZjJmNmZmLCAjZThmMGZmKTsKICBjb2xvcjogIzJlNjhkMTsKICBib3gtc2hhZG93OiBpbnNldCAwIDFweCAwIHJnYmEoMjU1LDI1NSwyNTUsLjkpOwogIHRyYW5zaXRpb246IGNvbG9yIC4xOHMgZWFzZSwgYm9yZGVyLWNvbG9yIC4xOHMgZWFzZSwKICAgICAgICAgICAgICBiYWNrZ3JvdW5kIC4xOHMgZWFzZSwgdHJhbnNmb3JtIC4xOHMgZWFzZTsKfQoKLmJhbS1ndWFyZC1pY29uLXY2MCBzdmcgewogIHdpZHRoOiAyMnB4OwogIGhlaWdodDogMjJweDsKICBmaWxsOiBub25lOwogIHN0cm9rZTogY3VycmVudENvbG9yOwogIHN0cm9rZS13aWR0aDogMS44OwogIHN0cm9rZS1saW5lY2FwOiByb3VuZDsKICBzdHJva2UtbGluZWpvaW46IHJvdW5kOwp9CgouYmFtLWd1YXJkLXJvdy12NjAuaXMtZW5hYmxlZC12NjAgLmJhbS1ndWFyZC1pY29uLXY2MCB7CiAgYm9yZGVyLWNvbG9yOiAjYmZlN2Q3OwogIGJhY2tncm91bmQ6IGxpbmVhci1ncmFkaWVudCgxNDVkZWcsICNlOWZhZjIsICNkZWY1ZWEpOwogIGNvbG9yOiAjMTE4MjVhOwogIHRyYW5zZm9ybTogdHJhbnNsYXRlWSgtMXB4KTsKfQoKLmJhbS1ndWFyZC10ZXh0LXY2MCB7CiAgbWluLXdpZHRoOiAwOwogIGRpc3BsYXk6IGZsZXg7CiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjsKICBhbGlnbi1pdGVtczogZmxleC1zdGFydDsKICBnYXA6IDZweDsKfQoKLmJhbS1ndWFyZC10ZXh0LXY2MCA+IHN0cm9uZywKLmJhbS1ndWFyZC10ZXh0LXY2MCA+IGgyLAouYmFtLWd1YXJkLXRleHQtdjYwID4gaDMsCi5iYW0tZ3VhcmQtdGV4dC12NjAgPiBoNCB7CiAgbWFyZ2luOiAwICFpbXBvcnRhbnQ7CiAgY29sb3I6ICMyMDM0NTIgIWltcG9ydGFudDsKICBmb250LXNpemU6IDE3cHggIWltcG9ydGFudDsKICBsaW5lLWhlaWdodDogMS4yICFpbXBvcnRhbnQ7CiAgZm9udC13ZWlnaHQ6IDgwMCAhaW1wb3J0YW50Owp9CgouYmFtLWd1YXJkLXRleHQtdjYwID4gc21hbGwsCi5iYW0tZ3VhcmQtdGV4dC12NjAgPiBwIHsKICBtYXJnaW46IDAgIWltcG9ydGFudDsKICBjb2xvcjogIzc4OGFhMyAhaW1wb3J0YW50OwogIGZvbnQtc2l6ZTogMTJweCAhaW1wb3J0YW50OwogIGxpbmUtaGVpZ2h0OiAxLjQ1ICFpbXBvcnRhbnQ7Cn0KCiNjaGF0LXBhbmVsIC5ndWFyZC1iYW5uZXIuYmFtLWd1YXJkLXJvdy12NjAgLnN3aXRjaCB7CiAgZmxleDogbm9uZTsKICBtYXJnaW4tbGVmdDogYXV0byAhaW1wb3J0YW50Owp9CgovKiBUaGUgdmlzaWJsZSBCQU0gQXNzaXN0IGh1YiBsYXVuY2hlci4gKi8KI2JhbS1hc3Npc3QtbGF1bmNoZXIgLmJhbS1hc3Npc3QtbGF1bmNoZXItbWFyaywKI2JhbS1hc3Npc3QtbGF1bmNoZXIgLmJhbS1hc3Npc3QtbGF1bmNoZXItY29weSwKI2JhbS1hc3Npc3QtbGF1bmNoZXIgLmJhbS1hc3Npc3Qtb25saW5lLAojYmFtLWFzc2lzdC1sYXVuY2hlciAuYmFtLWFzc2lzdC1jaGV2cm9uIHsKICBkaXNwbGF5OiBub25lICFpbXBvcnRhbnQ7Cn0KCiNiYW0tYXNzaXN0LWxhdW5jaGVyLmJhbS1hc3Npc3QtbGF1bmNoZXItdjYwIHsKICBpc29sYXRpb246IGlzb2xhdGU7CiAgd2lkdGg6IGF1dG8gIWltcG9ydGFudDsKICBtaW4td2lkdGg6IDIzOHB4ICFpbXBvcnRhbnQ7CiAgaGVpZ2h0OiA2OHB4ICFpbXBvcnRhbnQ7CiAgZGlzcGxheTogZmxleCAhaW1wb3J0YW50OwogIGFsaWduLWl0ZW1zOiBjZW50ZXIgIWltcG9ydGFudDsKICBnYXA6IDExcHggIWltcG9ydGFudDsKICBwYWRkaW5nOiA4cHggMTNweCA4cHggOXB4ICFpbXBvcnRhbnQ7CiAgb3ZlcmZsb3c6IHZpc2libGUgIWltcG9ydGFudDsKICBib3JkZXI6IDFweCBzb2xpZCByZ2JhKDI1NSwyNTUsMjU1LC40NSkgIWltcG9ydGFudDsKICBib3JkZXItcmFkaXVzOiAyMXB4ICFpbXBvcnRhbnQ7CiAgYmFja2dyb3VuZDoKICAgIHJhZGlhbC1ncmFkaWVudChjaXJjbGUgYXQgMTUlIC0yNSUsIHJnYmEoMTAzLDIzMSwyNTUsLjgyKSwgdHJhbnNwYXJlbnQgNDElKSwKICAgIGxpbmVhci1ncmFkaWVudCgxMzVkZWcsICMxMDJiNmYgMCUsICMxNTVlZDQgNTQlLCAjMTY4ZmM2IDEwMCUpICFpbXBvcnRhbnQ7CiAgY29sb3I6ICNmZmYgIWltcG9ydGFudDsKICBib3gtc2hhZG93OgogICAgMCAxOHB4IDQycHggcmdiYSgxNiw1NSwxMzIsLjQpLAogICAgaW5zZXQgMCAxcHggMCByZ2JhKDI1NSwyNTUsMjU1LC4yOCkgIWltcG9ydGFudDsKICBhbmltYXRpb246IGJhbS1hc3Npc3QtZmxvYXQtdjYwIDQuMnMgZWFzZS1pbi1vdXQgaW5maW5pdGU7CiAgdHJhbnNpdGlvbjogdHJhbnNmb3JtIC4ycyBlYXNlLCBib3gtc2hhZG93IC4ycyBlYXNlLAogICAgICAgICAgICAgIGZpbHRlciAuMnMgZWFzZSAhaW1wb3J0YW50Owp9CgojYmFtLWFzc2lzdC1sYXVuY2hlci5iYW0tYXNzaXN0LWxhdW5jaGVyLXY2MDo6YmVmb3JlIHsKICBjb250ZW50OiAiIjsKICBwb3NpdGlvbjogYWJzb2x1dGU7CiAgei1pbmRleDogLTE7CiAgaW5zZXQ6IC01cHg7CiAgYm9yZGVyOiAxcHggc29saWQgcmdiYSg3NCwxODgsMjU1LC4zKTsKICBib3JkZXItcmFkaXVzOiAyNXB4OwogIGFuaW1hdGlvbjogYmFtLWFzc2lzdC1yaW5nLXY2MCAyLjlzIGVhc2Utb3V0IGluZmluaXRlOwp9CgojYmFtLWFzc2lzdC1sYXVuY2hlci5iYW0tYXNzaXN0LWxhdW5jaGVyLXY2MDo6YWZ0ZXIgewogIGNvbnRlbnQ6ICIiOwogIHBvc2l0aW9uOiBhYnNvbHV0ZTsKICBpbnNldDogMXB4OwogIG92ZXJmbG93OiBoaWRkZW47CiAgYm9yZGVyLXJhZGl1czogMjBweDsKICBwb2ludGVyLWV2ZW50czogbm9uZTsKICBiYWNrZ3JvdW5kOiBsaW5lYXItZ3JhZGllbnQoCiAgICAxMDVkZWcsCiAgICB0cmFuc3BhcmVudCAyMiUsCiAgICByZ2JhKDI1NSwyNTUsMjU1LC4yKSA0NyUsCiAgICB0cmFuc3BhcmVudCA3MCUKICApOwogIHRyYW5zZm9ybTogdHJhbnNsYXRlWCgtMTMwJSk7CiAgYW5pbWF0aW9uOiBiYW0tYXNzaXN0LXNoZWVuLXY2MCA1LjhzIGVhc2UtaW4tb3V0IGluZmluaXRlOwp9CgojYmFtLWFzc2lzdC1sYXVuY2hlci5iYW0tYXNzaXN0LWxhdW5jaGVyLXY2MDpob3ZlciB7CiAgdHJhbnNmb3JtOiB0cmFuc2xhdGVZKC00cHgpIHNjYWxlKDEuMDIpICFpbXBvcnRhbnQ7CiAgZmlsdGVyOiBzYXR1cmF0ZSgxLjA4KSBicmlnaHRuZXNzKDEuMDQpOwogIGJveC1zaGFkb3c6CiAgICAwIDI0cHggNTJweCByZ2JhKDE2LDU1LDEzMiwuNDgpLAogICAgaW5zZXQgMCAxcHggMCByZ2JhKDI1NSwyNTUsMjU1LC4zMikgIWltcG9ydGFudDsKfQoKLmJhbS1hc3Npc3QtbGF1bmNoZXItbWFyay12NjAgewogIHdpZHRoOiA0OHB4OwogIGhlaWdodDogNDhweDsKICBkaXNwbGF5OiBncmlkICFpbXBvcnRhbnQ7CiAgcGxhY2UtaXRlbXM6IGNlbnRlcjsKICBmbGV4OiAwIDAgNDhweDsKICBvdmVyZmxvdzogaGlkZGVuOwogIGJvcmRlcjogMXB4IHNvbGlkIHJnYmEoMjU1LDI1NSwyNTUsLjM0KTsKICBib3JkZXItcmFkaXVzOiAxNXB4OwogIGJhY2tncm91bmQ6IGxpbmVhci1ncmFkaWVudCgKICAgIDE0NWRlZywKICAgIHJnYmEoMjU1LDI1NSwyNTUsLjI1KSwKICAgIHJnYmEoMjU1LDI1NSwyNTUsLjA4KQogICk7CiAgYm94LXNoYWRvdzoKICAgIGluc2V0IDAgMXB4IDAgcmdiYSgyNTUsMjU1LDI1NSwuMjgpLAogICAgMCA4cHggMjBweCByZ2JhKDUsMzQsMTAzLC4yMik7Cn0KCi5iYW0tY2hhdC1pY29uLXY2MCB7CiAgd2lkdGg6IDM0cHg7CiAgaGVpZ2h0OiAzNHB4OwogIG92ZXJmbG93OiB2aXNpYmxlOwp9CgouYmFtLWNoYXQtc2hlbGwtdjYwIHsKICBmaWxsOiBub25lOwogIHN0cm9rZTogI2ZmZjsKICBzdHJva2Utd2lkdGg6IDIuMTU7CiAgc3Ryb2tlLWxpbmVjYXA6IHJvdW5kOwogIHN0cm9rZS1saW5lam9pbjogcm91bmQ7Cn0KCi5iYW0tY2hhdC1kb3QtdjYwIHsKICBmaWxsOiAjZmZmOwogIGFuaW1hdGlvbjogYmFtLWNoYXQtZG90LXY2MCAxLjhzIGVhc2UtaW4tb3V0IGluZmluaXRlOwp9CgouYmFtLWNoYXQtZG90LXY2MC5kb3QtMiB7IGFuaW1hdGlvbi1kZWxheTogLjE2czsgfQouYmFtLWNoYXQtZG90LXY2MC5kb3QtMyB7IGFuaW1hdGlvbi1kZWxheTogLjMyczsgfQoKLmJhbS1jaGF0LXNwYXJrLXY2MCB7CiAgZmlsbDogI2U0ZmJmZjsKICB0cmFuc2Zvcm0tb3JpZ2luOiAzN3B4IDEwcHg7CiAgYW5pbWF0aW9uOiBiYW0tY2hhdC1zcGFyay12NjAgMi41cyBlYXNlLWluLW91dCBpbmZpbml0ZTsKfQoKLmJhbS1hc3Npc3QtbGF1bmNoZXItY29weS12NjAgewogIG1pbi13aWR0aDogMTA0cHg7CiAgZGlzcGxheTogZmxleCAhaW1wb3J0YW50OwogIGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47CiAgYWxpZ24taXRlbXM6IGZsZXgtc3RhcnQ7CiAgZ2FwOiA1cHg7CiAgdGV4dC1hbGlnbjogbGVmdDsKfQoKLmJhbS1hc3Npc3QtbGF1bmNoZXItY29weS12NjAgc3Ryb25nIHsKICBjb2xvcjogI2ZmZiAhaW1wb3J0YW50OwogIGZvbnQtc2l6ZTogMTRweCAhaW1wb3J0YW50OwogIGxpbmUtaGVpZ2h0OiAxICFpbXBvcnRhbnQ7CiAgZm9udC13ZWlnaHQ6IDg1MCAhaW1wb3J0YW50OwogIHdoaXRlLXNwYWNlOiBub3dyYXA7Cn0KCi5iYW0tYXNzaXN0LWxhdW5jaGVyLWNvcHktdjYwIHNtYWxsIHsKICBjb2xvcjogI2Q5ZWFmZiAhaW1wb3J0YW50OwogIGZvbnQtc2l6ZTogOXB4ICFpbXBvcnRhbnQ7CiAgbGluZS1oZWlnaHQ6IDEgIWltcG9ydGFudDsKICBmb250LXdlaWdodDogNjUwICFpbXBvcnRhbnQ7CiAgd2hpdGUtc3BhY2U6IG5vd3JhcDsKfQoKLmJhbS1hc3Npc3QtcHJlc2VuY2UtdjYwIHsKICBkaXNwbGF5OiBpbmxpbmUtZmxleCAhaW1wb3J0YW50OwogIGFsaWduLWl0ZW1zOiBjZW50ZXI7CiAgZ2FwOiA1cHg7CiAgbWFyZ2luLWxlZnQ6IGF1dG87CiAgcGFkZGluZzogNXB4IDdweDsKICBib3JkZXI6IDFweCBzb2xpZCByZ2JhKDI1NSwyNTUsMjU1LC4xOCk7CiAgYm9yZGVyLXJhZGl1czogOTk5cHg7CiAgYmFja2dyb3VuZDogcmdiYSgzLDMwLDgyLC4yKTsKICBjb2xvcjogI2U4ZjdmZjsKICBmb250LXNpemU6IDdweDsKICBsaW5lLWhlaWdodDogMTsKICBmb250LXdlaWdodDogODAwOwogIHRleHQtdHJhbnNmb3JtOiB1cHBlcmNhc2U7Cn0KCi5iYW0tYXNzaXN0LXByZXNlbmNlLXY2MCBpIHsKICB3aWR0aDogNnB4OwogIGhlaWdodDogNnB4OwogIGJvcmRlci1yYWRpdXM6IDUwJTsKICBiYWNrZ3JvdW5kOiAjNGNlMmExOwogIGJveC1zaGFkb3c6IDAgMCAwIDNweCByZ2JhKDc2LDIyNiwxNjEsLjE2KTsKfQoKLmJhbS1hc3Npc3QtY2hldnJvbi12NjAgewogIHdpZHRoOiAxN3B4OwogIGhlaWdodDogMTdweDsKICBmbGV4OiBub25lOwogIGZpbGw6IG5vbmU7CiAgc3Ryb2tlOiAjZGNlYWZmOwogIHN0cm9rZS13aWR0aDogMS45OwogIHN0cm9rZS1saW5lY2FwOiByb3VuZDsKICBzdHJva2UtbGluZWpvaW46IHJvdW5kOwogIHRyYW5zaXRpb246IHRyYW5zZm9ybSAuMThzIGVhc2U7Cn0KCiNiYW0tYXNzaXN0LXNoZWxsLmlzLW9wZW4gLmJhbS1hc3Npc3QtY2hldnJvbi12NjAgewogIHRyYW5zZm9ybTogcm90YXRlKDE4MGRlZyk7Cn0KCi5iYW0tYXNzaXN0LXBhbmVsLW1hcmstdjYwLAouYmFtLWNoYXQtYXZhdGFyLXY2MCB7CiAgZGlzcGxheTogZ3JpZCAhaW1wb3J0YW50OwogIHBsYWNlLWl0ZW1zOiBjZW50ZXIgIWltcG9ydGFudDsKICBvdmVyZmxvdzogdmlzaWJsZSAhaW1wb3J0YW50OwogIGJvcmRlcjogMXB4IHNvbGlkIHJnYmEoMjU1LDI1NSwyNTUsLjMpICFpbXBvcnRhbnQ7CiAgYm9yZGVyLXJhZGl1czogMTVweCAhaW1wb3J0YW50OwogIGJhY2tncm91bmQ6IGxpbmVhci1ncmFkaWVudCgKICAgIDE0NWRlZywKICAgICM2OWRmZmYsCiAgICAjNGQ4OWZmIDU1JSwKICAgICM3MTU5ZWYKICApICFpbXBvcnRhbnQ7CiAgYm94LXNoYWRvdzogMCA5cHggMjJweCByZ2JhKDEyLDYwLDE1MywuMjUpICFpbXBvcnRhbnQ7Cn0KCi5iYW0tYXNzaXN0LXBhbmVsLW1hcmstdjYwIC5iYW0tY2hhdC1pY29uLXY2MCwKLmJhbS1jaGF0LWF2YXRhci12NjAgLmJhbS1jaGF0LWljb24tdjYwIHsKICB3aWR0aDogMzFweDsKICBoZWlnaHQ6IDMxcHg7Cn0KCkBrZXlmcmFtZXMgYmFtLWFzc2lzdC1mbG9hdC12NjAgewogIDAlLDEwMCUgeyB0cmFuc2Zvcm06IHRyYW5zbGF0ZVkoMCk7IH0KICA1MCUgeyB0cmFuc2Zvcm06IHRyYW5zbGF0ZVkoLTVweCk7IH0KfQoKQGtleWZyYW1lcyBiYW0tYXNzaXN0LXJpbmctdjYwIHsKICAwJSB7IHRyYW5zZm9ybTogc2NhbGUoLjk2KTsgb3BhY2l0eTogLjY4OyB9CiAgNzIlLDEwMCUgeyB0cmFuc2Zvcm06IHNjYWxlKDEuMDgpOyBvcGFjaXR5OiAwOyB9Cn0KCkBrZXlmcmFtZXMgYmFtLWFzc2lzdC1zaGVlbi12NjAgewogIDAlLDU4JSB7IHRyYW5zZm9ybTogdHJhbnNsYXRlWCgtMTMwJSk7IH0KICA3NyUsMTAwJSB7IHRyYW5zZm9ybTogdHJhbnNsYXRlWCgxMzAlKTsgfQp9CgpAa2V5ZnJhbWVzIGJhbS1jaGF0LWRvdC12NjAgewogIDAlLDU1JSwxMDAlIHsgb3BhY2l0eTogLjQ2OyB0cmFuc2Zvcm06IHRyYW5zbGF0ZVkoMCk7IH0KICAyNiUgeyBvcGFjaXR5OiAxOyB0cmFuc2Zvcm06IHRyYW5zbGF0ZVkoLTJweCk7IH0KfQoKQGtleWZyYW1lcyBiYW0tY2hhdC1zcGFyay12NjAgewogIDAlLDEwMCUgeyBvcGFjaXR5OiAuNzI7IHRyYW5zZm9ybTogc2NhbGUoLjg2KSByb3RhdGUoMGRlZyk7IH0KICA1MCUgeyBvcGFjaXR5OiAxOyB0cmFuc2Zvcm06IHNjYWxlKDEuMTIpIHJvdGF0ZSgxMmRlZyk7IH0KfQoKQG1lZGlhKG1heC13aWR0aDo3NjBweCkgewogICNiYW0tYXNzaXN0LWxhdW5jaGVyLmJhbS1hc3Npc3QtbGF1bmNoZXItdjYwIHsKICAgIG1pbi13aWR0aDogNjRweCAhaW1wb3J0YW50OwogICAgd2lkdGg6IDY0cHggIWltcG9ydGFudDsKICAgIGhlaWdodDogNjRweCAhaW1wb3J0YW50OwogICAgcGFkZGluZzogN3B4ICFpbXBvcnRhbnQ7CiAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlciAhaW1wb3J0YW50OwogIH0KCiAgLmJhbS1hc3Npc3QtbGF1bmNoZXItY29weS12NjAsCiAgLmJhbS1hc3Npc3QtcHJlc2VuY2UtdjYwLAogIC5iYW0tYXNzaXN0LWNoZXZyb24tdjYwIHsKICAgIGRpc3BsYXk6IG5vbmUgIWltcG9ydGFudDsKICB9CgogICNjaGF0LXBhbmVsIC5ndWFyZC1iYW5uZXIuYmFtLWd1YXJkLXJvdy12NjAgewogICAgcGFkZGluZzogMTRweCAxNnB4ICFpbXBvcnRhbnQ7CiAgfQp9CgpAbWVkaWEocHJlZmVycy1yZWR1Y2VkLW1vdGlvbjpyZWR1Y2UpIHsKICAjYmFtLWFzc2lzdC1sYXVuY2hlci5iYW0tYXNzaXN0LWxhdW5jaGVyLXY2MCwKICAjYmFtLWFzc2lzdC1sYXVuY2hlci5iYW0tYXNzaXN0LWxhdW5jaGVyLXY2MDo6YmVmb3JlLAogICNiYW0tYXNzaXN0LWxhdW5jaGVyLmJhbS1hc3Npc3QtbGF1bmNoZXItdjYwOjphZnRlciwKICAuYmFtLWNoYXQtZG90LXY2MCwKICAuYmFtLWNoYXQtc3BhcmstdjYwIHsKICAgIGFuaW1hdGlvbjogbm9uZSAhaW1wb3J0YW50OwogIH0KfQo=').decode()
MAIN_CHAT_REPLACEMENT = base64.b64decode('IyBCQU1fQkFOS19VSV9SRVZJU0lPTl9WNjBfQ0hBVApkZWYgX2xvY2FsX2d1YXJkX2NvbnRlbnQoCiAgICByZXN1bHQ6IGRpY3QsCiAgICBmYWxsYmFjazogc3RyLAopIC0+IHN0cjoKICAgIHJlZGFjdGVkID0gcmVzdWx0LmdldCgicmVkYWN0ZWRSZXF1ZXN0IikKCiAgICBpZiBpc2luc3RhbmNlKHJlZGFjdGVkLCBkaWN0KToKICAgICAgICBwcm9tcHQgPSByZWRhY3RlZC5nZXQoInByb21wdCIpCiAgICAgICAgaWYgaXNpbnN0YW5jZShwcm9tcHQsIHN0cikgYW5kIHByb21wdDoKICAgICAgICAgICAgcmV0dXJuIHByb21wdAoKICAgICAgICB0cnk6CiAgICAgICAgICAgIGNvbnRlbnQgPSByZWRhY3RlZFsiY2hvaWNlcyJdWzBdWyJtZXNzYWdlIl1bImNvbnRlbnQiXQogICAgICAgIGV4Y2VwdCAoS2V5RXJyb3IsIEluZGV4RXJyb3IsIFR5cGVFcnJvcik6CiAgICAgICAgICAgIGNvbnRlbnQgPSBOb25lCgogICAgICAgIGlmIGlzaW5zdGFuY2UoY29udGVudCwgc3RyKSBhbmQgY29udGVudDoKICAgICAgICAgICAgcmV0dXJuIGNvbnRlbnQKCiAgICByZXR1cm4gZmFsbGJhY2sKCgphc3luYyBkZWYgX2NoYXRfd2l0aF9sb2NhbF9ndWFyZCgKICAgIG1lc3NhZ2U6IHN0ciwKKSAtPiBkaWN0OgogICAgcHJvbXB0X3Jlc3VsdCA9IGd1YXJkLl9sb2NhbF9zY2FuX3RleHQobWVzc2FnZSkKCiAgICBpZiBzdHIocHJvbXB0X3Jlc3VsdC5nZXQoImFjdGlvbiIsICJhbGxvdyIpKS5sb3dlcigpID09ICJibG9jayI6CiAgICAgICAgcmVhc29ucyA9IHByb21wdF9yZXN1bHQuZ2V0KCJyZWFzb25zIikgb3IgWwogICAgICAgICAgICBwcm9tcHRfcmVzdWx0LmdldCgKICAgICAgICAgICAgICAgICJyZWFzb24iLAogICAgICAgICAgICAgICAgIkFJIEd1YXJkIHBvbGljeSBlbmZvcmNlbWVudCIsCiAgICAgICAgICAgICkKICAgICAgICBdCgogICAgICAgIHJhaXNlIEd1YXJkQmxvY2tlZCgKICAgICAgICAgICAgIiwgIi5qb2luKHJlYXNvbnMpLAogICAgICAgICAgICBkZXRhaWxzPXByb21wdF9yZXN1bHQsCiAgICAgICAgKQoKICAgIHNhZmVfcHJvbXB0ID0gX2xvY2FsX2d1YXJkX2NvbnRlbnQoCiAgICAgICAgcHJvbXB0X3Jlc3VsdCwKICAgICAgICBtZXNzYWdlLAogICAgKQoKICAgIGxsbV9yZXNwb25zZSA9IGF3YWl0IGxsbS5jb21wbGV0ZSgKICAgICAgICBzYWZlX3Byb21wdCwKICAgICAgICB2dWxuZXJhYmxlPUZhbHNlLAogICAgKQoKICAgIHRyeToKICAgICAgICByYXdfb3V0cHV0ID0gc3RyKAogICAgICAgICAgICBsbG1fcmVzcG9uc2VbImNob2ljZXMiXVswXVsibWVzc2FnZSJdWyJjb250ZW50Il0KICAgICAgICApCiAgICBleGNlcHQgKEtleUVycm9yLCBJbmRleEVycm9yLCBUeXBlRXJyb3IpOgogICAgICAgIHJhd19vdXRwdXQgPSAiIgoKICAgIG91dHB1dF9yZXN1bHQgPSBndWFyZC5fbG9jYWxfc2Nhbl90ZXh0KHJhd19vdXRwdXQpCgogICAgaWYgc3RyKG91dHB1dF9yZXN1bHQuZ2V0KCJhY3Rpb24iLCAiYWxsb3ciKSkubG93ZXIoKSA9PSAiYmxvY2siOgogICAgICAgIHJlYXNvbnMgPSBvdXRwdXRfcmVzdWx0LmdldCgicmVhc29ucyIpIG9yIFsKICAgICAgICAgICAgb3V0cHV0X3Jlc3VsdC5nZXQoCiAgICAgICAgICAgICAgICAicmVhc29uIiwKICAgICAgICAgICAgICAgICJBSSBHdWFyZCByZXNwb25zZSBwb2xpY3kgZW5mb3JjZW1lbnQiLAogICAgICAgICAgICApCiAgICAgICAgXQoKICAgICAgICByYWlzZSBHdWFyZEJsb2NrZWQoCiAgICAgICAgICAgICIsICIuam9pbihyZWFzb25zKSwKICAgICAgICAgICAgZGV0YWlscz1vdXRwdXRfcmVzdWx0LAogICAgICAgICkKCiAgICByZXR1cm4gewogICAgICAgICJzdGF0dXMiOiAiYWxsb3dlZCIsCiAgICAgICAgIm1lc3NhZ2UiOiBfbG9jYWxfZ3VhcmRfY29udGVudCgKICAgICAgICAgICAgb3V0cHV0X3Jlc3VsdCwKICAgICAgICAgICAgcmF3X291dHB1dCwKICAgICAgICApLAogICAgICAgICJndWFyZCI6IHsKICAgICAgICAgICAgImVuYWJsZWQiOiBUcnVlLAogICAgICAgICAgICAibW9kZSI6ICJsb2NhbC1kZW1vIiwKICAgICAgICAgICAgImZhbGxiYWNrIjogVHJ1ZSwKICAgICAgICAgICAgImlucHV0IjogewogICAgICAgICAgICAgICAgImFjdGlvbiI6IHByb21wdF9yZXN1bHQuZ2V0KCJhY3Rpb24iLCAiYWxsb3ciKSwKICAgICAgICAgICAgICAgICJyZWFzb25zIjogcHJvbXB0X3Jlc3VsdC5nZXQoInJlYXNvbnMiLCBbXSksCiAgICAgICAgICAgIH0sCiAgICAgICAgICAgICJvdXRwdXQiOiB7CiAgICAgICAgICAgICAgICAiYWN0aW9uIjogb3V0cHV0X3Jlc3VsdC5nZXQoImFjdGlvbiIsICJhbGxvdyIpLAogICAgICAgICAgICAgICAgInJlYXNvbnMiOiBvdXRwdXRfcmVzdWx0LmdldCgicmVhc29ucyIsIFtdKSwKICAgICAgICAgICAgfSwKICAgICAgICB9LAogICAgfQoKCkBhcHAucG9zdCgiL2FwaS9jaGF0IikKYXN5bmMgZGVmIGNoYXQocGF5bG9hZDogQ2hhdFJlcXVlc3QpIC0+IGRpY3Q6CiAgICB0cnk6CiAgICAgICAgaWYgbm90IHBheWxvYWQuZ3VhcmRfZW5hYmxlZDoKICAgICAgICAgICAgdW5wcm90ZWN0ZWRfcmVzcG9uc2UgPSBhd2FpdCBsbG0uY29tcGxldGUoCiAgICAgICAgICAgICAgICBwYXlsb2FkLm1lc3NhZ2UsCiAgICAgICAgICAgICAgICB2dWxuZXJhYmxlPVRydWUsCiAgICAgICAgICAgICkKCiAgICAgICAgICAgIG1lc3NhZ2UgPSAoCiAgICAgICAgICAgICAgICB1bnByb3RlY3RlZF9yZXNwb25zZQogICAgICAgICAgICAgICAgLmdldCgiY2hvaWNlcyIsIFt7fV0pWzBdCiAgICAgICAgICAgICAgICAuZ2V0KCJtZXNzYWdlIiwge30pCiAgICAgICAgICAgICAgICAuZ2V0KCJjb250ZW50IiwgIiIpCiAgICAgICAgICAgICkKCiAgICAgICAgICAgIHJldHVybiB7CiAgICAgICAgICAgICAgICAic3RhdHVzIjogImFsbG93ZWQiLAogICAgICAgICAgICAgICAgIm1lc3NhZ2UiOiBtZXNzYWdlLAogICAgICAgICAgICAgICAgImd1YXJkIjogewogICAgICAgICAgICAgICAgICAgICJlbmFibGVkIjogRmFsc2UsCiAgICAgICAgICAgICAgICAgICAgImlucHV0IjogTm9uZSwKICAgICAgICAgICAgICAgICAgICAib3V0cHV0IjogTm9uZSwKICAgICAgICAgICAgICAgIH0sCiAgICAgICAgICAgIH0KCiAgICAgICAgY2ZnID0gcnVudGltZS5zbmFwc2hvdCgpCgogICAgICAgIGlmICgKICAgICAgICAgICAgbm90IGNmZ1siY29uZmlndXJlZCJdCiAgICAgICAgICAgIGFuZCBub3QgY2ZnWyJmb3JjZV9kZW1vX21vZGUiXQogICAgICAgICk6CiAgICAgICAgICAgIHJldHVybiBhd2FpdCBfY2hhdF93aXRoX2xvY2FsX2d1YXJkKAogICAgICAgICAgICAgICAgcGF5bG9hZC5tZXNzYWdlCiAgICAgICAgICAgICkKCiAgICAgICAgdHJ5OgogICAgICAgICAgICBwcm9tcHRfcmVzdWx0ID0gYXdhaXQgZ3VhcmQuaW5zcGVjdF9wcm9tcHQoCiAgICAgICAgICAgICAgICBwYXlsb2FkLm1lc3NhZ2UKICAgICAgICAgICAgKQogICAgICAgICAgICBzYWZlX3Byb21wdCA9IHByb21wdF9yZXN1bHQuZ2V0KAogICAgICAgICAgICAgICAgImNvbnRlbnQiLAogICAgICAgICAgICAgICAgcGF5bG9hZC5tZXNzYWdlLAogICAgICAgICAgICApCiAgICAgICAgICAgIGxsbV9yZXNwb25zZSA9IGF3YWl0IGxsbS5jb21wbGV0ZSgKICAgICAgICAgICAgICAgIHNhZmVfcHJvbXB0LAogICAgICAgICAgICAgICAgdnVsbmVyYWJsZT1GYWxzZSwKICAgICAgICAgICAgKQogICAgICAgICAgICBvdXRwdXRfcmVzdWx0ID0gYXdhaXQgZ3VhcmQuaW5zcGVjdF9yZXNwb25zZSgKICAgICAgICAgICAgICAgIGxsbV9yZXNwb25zZQogICAgICAgICAgICApCiAgICAgICAgZXhjZXB0IEd1YXJkVW5hdmFpbGFibGU6CiAgICAgICAgICAgIGxvZ2dlci53YXJuaW5nKAogICAgICAgICAgICAgICAgIkxpdmUgQUkgR3VhcmQgdW5hdmFpbGFibGU7IHVzaW5nIGxvY2FsIHBvbGljeSAiCiAgICAgICAgICAgICAgICAic2ltdWxhdGlvbiBmb3IgdGhlIGludGVyYWN0aXZlIGRlbW8uIiwKICAgICAgICAgICAgICAgIGV4Y19pbmZvPVRydWUsCiAgICAgICAgICAgICkKICAgICAgICAgICAgcmV0dXJuIGF3YWl0IF9jaGF0X3dpdGhfbG9jYWxfZ3VhcmQoCiAgICAgICAgICAgICAgICBwYXlsb2FkLm1lc3NhZ2UKICAgICAgICAgICAgKQoKICAgICAgICByZXR1cm4gewogICAgICAgICAgICAic3RhdHVzIjogImFsbG93ZWQiLAogICAgICAgICAgICAibWVzc2FnZSI6IG91dHB1dF9yZXN1bHQuZ2V0KCJjb250ZW50IiwgIiIpLAogICAgICAgICAgICAiZ3VhcmQiOiB7CiAgICAgICAgICAgICAgICAiZW5hYmxlZCI6IFRydWUsCiAgICAgICAgICAgICAgICAibW9kZSI6ICJsaXZlIiwKICAgICAgICAgICAgICAgICJmYWxsYmFjayI6IEZhbHNlLAogICAgICAgICAgICAgICAgImlucHV0IjogewogICAgICAgICAgICAgICAgICAgICJhY3Rpb24iOiBwcm9tcHRfcmVzdWx0LmdldCgiYWN0aW9uIiwgImFsbG93IiksCiAgICAgICAgICAgICAgICAgICAgInJlYXNvbnMiOiBwcm9tcHRfcmVzdWx0LmdldCgicmVhc29ucyIsIFtdKSwKICAgICAgICAgICAgICAgIH0sCiAgICAgICAgICAgICAgICAib3V0cHV0IjogewogICAgICAgICAgICAgICAgICAgICJhY3Rpb24iOiBvdXRwdXRfcmVzdWx0LmdldCgiYWN0aW9uIiwgImFsbG93IiksCiAgICAgICAgICAgICAgICAgICAgInJlYXNvbnMiOiBvdXRwdXRfcmVzdWx0LmdldCgicmVhc29ucyIsIFtdKSwKICAgICAgICAgICAgICAgIH0sCiAgICAgICAgICAgIH0sCiAgICAgICAgfQoKICAgIGV4Y2VwdCBHdWFyZEJsb2NrZWQgYXMgZXhjOgogICAgICAgIHJlYXNvbnMgPSAoCiAgICAgICAgICAgIGV4Yy5kZXRhaWxzLmdldCgicmVhc29ucyIpCiAgICAgICAgICAgIG9yIFtleGMucmVhc29uXQogICAgICAgICkKCiAgICAgICAgcmV0dXJuIEpTT05SZXNwb25zZSgKICAgICAgICAgICAgc3RhdHVzX2NvZGU9NDAwLAogICAgICAgICAgICBjb250ZW50PXsKICAgICAgICAgICAgICAgICJzdGF0dXMiOiAiYmxvY2tlZCIsCiAgICAgICAgICAgICAgICAibWVzc2FnZSI6ICgKICAgICAgICAgICAgICAgICAgICAiQmxvY2tlZCBieSBUcmVuZCBWaXNpb24gT25lICIKICAgICAgICAgICAgICAgICAgICAiQUkgR3VhcmQgcG9saWN5LiIKICAgICAgICAgICAgICAgICksCiAgICAgICAgICAgICAgICAicmVhc29ucyI6IHJlYXNvbnMsCiAgICAgICAgICAgICAgICAiZ3VhcmQiOiB7CiAgICAgICAgICAgICAgICAgICAgImVuYWJsZWQiOiBUcnVlLAogICAgICAgICAgICAgICAgICAgICJtb2RlIjogZXhjLmRldGFpbHMuZ2V0KAogICAgICAgICAgICAgICAgICAgICAgICAiZW5naW5lIiwKICAgICAgICAgICAgICAgICAgICAgICAgInBvbGljeSIsCiAgICAgICAgICAgICAgICAgICAgKSwKICAgICAgICAgICAgICAgIH0sCiAgICAgICAgICAgIH0sCiAgICAgICAgKQoKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZXhjOgogICAgICAgIGxvZ2dlci5leGNlcHRpb24oIkNoYXQgcmVxdWVzdCBmYWlsZWQiKQogICAgICAgIHJhaXNlIEhUVFBFeGNlcHRpb24oCiAgICAgICAgICAgIHN0YXR1c19jb2RlPTUwMiwKICAgICAgICAgICAgZGV0YWlsPSgKICAgICAgICAgICAgICAgICJUaGUgYXNzaXN0YW50IGNvdWxkIG5vdCAiCiAgICAgICAgICAgICAgICAicHJvY2VzcyB0aGlzIHJlcXVlc3QuIgogICAgICAgICAgICApLAogICAgICAgICkgZnJvbSBleGMKCgphc3luYyBkZWYgX3NjYW5uZXJfY29tcGxldGlvbg==').decode()

ALLOWED_DIRTY_FILES = {
    "app/main.py",
    "app/services.py",
    "app/vision_one_live.py",
    "app/static/index.html",
    "app/static/app.js",
    "app/static/styles.css",
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def run(command, cwd=None, check=True, capture=False):
    print("+", " ".join(str(item) for item in command))
    result = subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout)
        if capture and result.stderr:
            print(result.stderr, file=sys.stderr)
        fail(f"Command failed with exit code {result.returncode}")
    return result


def require(name: str) -> None:
    if not shutil.which(name):
        fail(f"{name} is not installed")


def parse_dirty_files(output: str) -> set[str]:
    files = set()
    for raw_line in output.splitlines():
        if not raw_line:
            continue
        if len(raw_line) >= 4 and raw_line[2] == " ":
            path = raw_line[3:]
        else:
            match = re.match(r"^.{2}\s(.*)$", raw_line)
            if not match:
                fail("Unable to parse Git status entry: " + repr(raw_line))
            path = match.group(1)
        path = path.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.add(path)
    return files


def validate_dirty_state(root: Path) -> None:
    raw = run(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=root,
        capture=True,
    ).stdout
    if not raw.strip():
        return
    unexpected = parse_dirty_files(raw) - ALLOWED_DIRTY_FILES
    if unexpected:
        fail(
            "Unexpected tracked changes are present: "
            + ", ".join(sorted(unexpected))
        )
    print("Detected expected source changes; continuing safely.")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"{label}: already applied")
        return text
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def retire_v58(text: str) -> str:
    if "BAM_BANK_UI_REVISION_V58_RETIRED_BY_V60" in text:
        return text
    start = text.find("/* BAM_BANK_UI_REVISION_V58 */")
    end = text.find("/* BAM_BANK_UI_REVISION_V59_1 */", start + 1)
    if start < 0 or end < 0:
        fail("Unable to locate the active Revision 58 block")
    replacement = (
        "/* BAM_BANK_UI_REVISION_V58_RETIRED_BY_V60\n"
        " * Removed because it enumerated unrelated runtime checkboxes\n"
        " * and coupled AI Guard to ZTSA.\n"
        " */\n\n"
    )
    return text[:start] + replacement + text[end:]


def patch_frontend(root: Path) -> None:
    js_path = root / "app/static/app.js"
    css_path = root / "app/static/styles.css"
    index_path = root / "app/static/index.html"

    js = js_path.read_text(encoding="utf-8")

    old_api = '''  if (!response.ok) {
    const detail = body?.detail || body?.message || body || `HTTP ${response.status}`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
'''
    new_api = '''  if (!response.ok) {
    const detail =
      body?.detail ||
      body?.message ||
      body ||
      `HTTP ${response.status}`;
    const error = new Error(
      typeof detail === 'string'
        ? detail
        : JSON.stringify(detail)
    );
    error.payload = body;
    error.status = response.status;
    throw error;
  }
'''
    js = replace_once(js, old_api, new_api, "Structured API errors")

    old_chat = '''  } catch (error) {
    let reasons = [];
    try {
      const parsed = JSON.parse(error.message);
      reasons = parsed.reasons || [];
    } catch (_) {}
    appendMessage('blocked', 'The request was blocked or could not be processed.', reasons.length ? reasons : [error.message]);
  } finally {
'''
    new_chat = '''  } catch (error) {
    const payload =
      error?.payload &&
      typeof error.payload === 'object'
        ? error.payload
        : {};

    const reasons =
      Array.isArray(payload.reasons)
        ? payload.reasons
        : [];

    const blocked =
      payload.status === 'blocked' ||
      error.status === 400;

    appendMessage(
      'blocked',
      blocked
        ? (
            payload.message ||
            'Blocked by Trend Vision One AI Guard policy.'
          )
        : 'The assistant could not process this request.',
      reasons.length
        ? reasons
        : [
            blocked
              ? 'AI Guard policy enforcement'
              : 'Service temporarily unavailable'
          ]
    );
  } finally {
'''
    js = replace_once(js, old_chat, new_chat, "Friendly chat errors")

    old_availability = '''    const available = guardSettings.forceDemoMode || guardSettings.configured;
    state.guardEnabled = available;
    safeChecked('#guard-toggle', available);
    safeDisabled('#guard-toggle', !available);
    safeText('#guard-mode-label', available
      ? 'Protected · prompts and responses inspected'
      : 'Protection unavailable');
'''
    new_availability = '''    const liveAvailable =
      guardSettings.forceDemoMode ||
      guardSettings.configured;

    state.guardEnabled = Boolean(liveAvailable);
    safeChecked('#guard-toggle', liveAvailable);

    // The presenter can always compare protected and unprotected
    // chat paths. Without a live key, /api/chat uses an honest
    // local policy simulation and does not claim a Vision One call.
    safeDisabled('#guard-toggle', false);

    safeText(
      '#guard-mode-label',
      liveAvailable
        ? 'Protected · prompts and responses inspected'
        : 'Unprotected demo · enable AI Guard for local policy simulation'
    );
'''
    js = replace_once(
        js,
        old_availability,
        new_availability,
        "AI Guard demo availability",
    )

    if "BAM_BANK_UI_REVISION_V60" not in js:
        js = retire_v58(js)
        js = js.rstrip() + "\n\n" + V60_JS.strip() + "\n"

    js_path.write_text(js, encoding="utf-8")

    css = css_path.read_text(encoding="utf-8")
    if "BAM_BANK_UI_REVISION_V60" not in css:
        css = css.rstrip() + "\n\n" + V60_CSS.strip() + "\n"
    css_path.write_text(css, encoding="utf-8")

    index = index_path.read_text(encoding="utf-8")
    for asset in ("styles.css", "app.js", "favicon.svg"):
        index = re.sub(
            rf"/static/{re.escape(asset)}\?v=[0-9.]+",
            f"/static/{asset}?v={VERSION}",
            index,
        )
    marker = "<!-- BAM_BANK_UI_REVISION_V60 -->"
    if marker not in index:
        index = index.replace("</body>", f"  {marker}\n</body>", 1)
    index_path.write_text(index, encoding="utf-8")


def patch_backend(root: Path) -> None:
    main_path = root / "app/main.py"
    services_path = root / "app/services.py"

    main = main_path.read_text(encoding="utf-8")
    main = re.sub(
        r'version="[0-9.]+"',
        f'version="{VERSION}"',
        main,
        count=1,
    )
    main = re.sub(
        r'"version":\s*"[0-9.]+"',
        f'"version": "{VERSION}"',
        main,
        count=1,
    )

    if "# BAM_BANK_UI_REVISION_V60_CHAT" not in main:
        pattern = re.compile(
            r'@app\.post\("/api/chat"\)[\s\S]*?\n\nasync def _scanner_completion'
        )
        main, count = pattern.subn(
            MAIN_CHAT_REPLACEMENT.strip(),
            main,
            count=1,
        )
        if count != 1:
            fail("Unable to replace the current /api/chat handler")

    main_path.write_text(main, encoding="utf-8")

    services = services_path.read_text(encoding="utf-8")
    old_rule = r'r"\b(phishing|credential[- ]?stealing|malware)\b",'
    new_rule = (
        r'r"\b(phishing|credential[- ]?stealing|malware|bomb|bom|'
        r'nuclear|nuklir|explosive|weapon|senjata)\b",'
    )
    if new_rule not in services:
        if old_rule not in services:
            fail("Unable to locate the local harmful-content rule")
        services = services.replace(old_rule, new_rule, 1)
    services_path.write_text(services, encoding="utf-8")


def validate_sources(root: Path) -> None:
    run(
        [
            sys.executable,
            "-m",
            "py_compile",
            "app/main.py",
            "app/services.py",
            "app/vision_one_live.py",
        ],
        cwd=root,
    )
    run(["git", "diff", "--check"], cwd=root)

    node = shutil.which("node")
    if node:
        run([node, "--check", "app/static/app.js"], cwd=root)
    elif subprocess.run(
        ["docker", "image", "inspect", "node:22-alpine"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0:
        run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{root / 'app/static'}:/work:ro",
                "node:22-alpine",
                "node",
                "--check",
                "/work/app.js",
            ],
            cwd=root,
        )
    else:
        print("Node.js is unavailable; Revision 60 JS was pre-validated.")

    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    required = (
        "BAM_BANK_UI_REVISION_V60",
        "BAM_BANK_UI_REVISION_V58_RETIRED_BY_V60",
        "bam-assist-launcher-v60",
        "bam-guard-row-v60",
    )
    missing = [item for item in required if item not in js]
    if missing:
        fail("Frontend validation missing: " + ", ".join(missing))
    if "function guardInputs()" in js:
        fail("The coupled Revision 58 guardInputs() is still active")


def read_health():
    result = subprocess.run(
        ["curl", "-fsS", f"http://127.0.0.1:{PORT}/api/health"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def deploy(root: Path):
    run(["docker", "build", "--no-cache", "-t", IMAGE, "."], cwd=root)

    old_ids = run(
        ["docker", "ps", "-q", "--filter", f"publish={PORT}"],
        cwd=root,
        capture=True,
    ).stdout.strip().split()
    for container_id in old_ids:
        run(["docker", "rm", "-f", container_id], cwd=root, check=False)

    for name in (
        "bambank-demo-v56",
        "bambank-demo-v57",
        "bambank-demo-v58",
        "bambank-demo-v59",
        "bambank-demo-v59-1",
        "bambank-demo-v59-2",
        "bambank-demo-restored",
        "visionone-bank-demo-test",
        CONTAINER,
    ):
        run(["docker", "rm", "-f", name], cwd=root, check=False)

    run(["docker", "volume", "create", "bambank-demo-data"], cwd=root, check=False)

    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER,
            "--restart",
            "unless-stopped",
            "-p",
            f"{PORT}:8080",
            "--env-file",
            str(root / ".env"),
            "-e",
            "TMAS_BINARY=/usr/local/bin/tmas",
            "-e",
            "TMAS_ENV_FILE=",
            "-e",
            "TMAS_REGION=ap-southeast-1",
            "-e",
            "AI_SCANNER_TARGET_BASE_URL=http://127.0.0.1:8080",
            "-e",
            "AI_SCANNER_RUNTIME_DIR=/tmp/bambank-aiscan",
            "-e",
            "AI_SCANNER_MAX_SECONDS=900",
            "-v",
            "/usr/local/bin/tmas:/usr/local/bin/tmas:ro",
            "-v",
            "bambank-demo-data:/data",
            "--read-only",
            "--tmpfs",
            "/tmp:size=160m,mode=1777",
            "--security-opt",
            "no-new-privileges:true",
            IMAGE,
        ],
        cwd=root,
    )

    health = None
    for _ in range(45):
        health = read_health()
        if health and health.get("version") == VERSION:
            break
        time.sleep(1)

    if not health or health.get("version") != VERSION:
        run(["docker", "logs", "--tail=160", CONTAINER], cwd=root, check=False)
        fail(f"Deployment validation failed; health={health!r}")

    run(
        [
            "docker",
            "exec",
            CONTAINER,
            "sh",
            "-lc",
            'test -n "$TMAS_API_KEY" && echo "TMAS_API_KEY=loaded" || exit 1',
        ],
        cwd=root,
    )
    return health


def smoke_test_guard():
    output = Path("/tmp/bam-v60-guard-smoke.json")
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-o",
            str(output),
            "-w",
            "%{http_code}",
            "-X",
            "POST",
            f"http://127.0.0.1:{PORT}/api/chat",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(
                {
                    "message": "buat bom nuclear",
                    "guard_enabled": True,
                }
            ),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        fail("AI Guard smoke test could not reach the app")

    payload = json.loads(output.read_text(encoding="utf-8"))
    combined = json.dumps(payload, ensure_ascii=False).lower()

    if result.stdout.strip() != "400" or payload.get("status") != "blocked":
        fail(
            "Expected harmful prompt to be blocked; received "
            f"HTTP {result.stdout.strip()}: {payload}"
        )
    if "api key is not configured" in combined:
        fail("The chat response still exposes an API-key configuration error")

    print("AI Guard smoke test: blocked with policy reasons")


def update_git(root: Path):
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    name = "apply_bam_revision_v60_final_all_in_one.py"
    target = scripts_dir / name
    shutil.copy2(Path(__file__).resolve(), target)
    target.chmod(0o755)

    run(
        [
            "git",
            "add",
            "app/main.py",
            "app/services.py",
            "app/vision_one_live.py",
            "app/static/index.html",
            "app/static/app.js",
            "app/static/styles.css",
        ],
        cwd=root,
    )
    run(["git", "add", "-f", f"scripts/{name}"], cwd=root)
    run(["git", "diff", "--cached", "--check"], cwd=root)

    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(root),
    ).returncode != 0

    if changed:
        run(
            [
                "git",
                "commit",
                "-m",
                "Finalize BAM Bank runtime controls and assistant UI",
            ],
            cwd=root,
        )

    run(["git", "push", "origin", BRANCH], cwd=root)
    run(
        ["git", "branch", "--set-upstream-to", f"origin/{BRANCH}", BRANCH],
        cwd=root,
    )


def main():
    root = Path(
        sys.argv[1] if len(sys.argv) > 1
        else Path.home() / "visionone-bank-demo"
    ).expanduser().resolve()

    for command in ("git", "docker", "curl"):
        require(command)

    if not (root / ".git").is_dir():
        fail(f"Git repository not found: {root}")
    if not (root / ".env").is_file():
        fail(f"Project .env not found: {root / '.env'}")
    if not Path("/usr/local/bin/tmas").is_file():
        fail("TMAS binary not found: /usr/local/bin/tmas")

    run(["git", "fetch", "origin", "--prune"], cwd=root)
    branch = run(
        ["git", "branch", "--show-current"],
        cwd=root,
        capture=True,
    ).stdout.strip()
    if branch != BRANCH:
        fail(f"Expected branch {BRANCH}, current branch is {branch!r}")

    validate_dirty_state(root)

    backup_dir = Path("/tmp") / (
        "bam-v60-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    for relative in (
        "app/main.py",
        "app/services.py",
        "app/static/index.html",
        "app/static/app.js",
        "app/static/styles.css",
    ):
        source = root / relative
        target = backup_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"Source backup: {backup_dir}")

    patch_backend(root)
    patch_frontend(root)
    validate_sources(root)
    health = deploy(root)
    smoke_test_guard()
    update_git(root)

    print()
    print("BAM Bank Revision 60 completed.")
    print(f"Version   : {VERSION}")
    print(f"Branch    : {BRANCH}")
    print(f"Container : {CONTAINER}")
    print(f"Health    : {health}")
    print()
    print("Fixed:")
    print("  - AI Guard and ZTSA toggles are independent")
    print("  - Missing live Guard key uses local chat policy simulation")
    print("  - Block messages show policy reasons, not credential errors")
    print("  - AI Guard icon and row layout are proportional")
    print('  - "File security ready" text badge is removed')
    print("  - The visible BAM Assist launcher uses an animated chat icon")


if __name__ == "__main__":
    main()
