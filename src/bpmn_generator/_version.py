"""Số phiên bản, một chỗ duy nhất.

Tách ra thành module riêng vì hai nơi cần nó và chúng không import được nhau:
`__init__.py` công bố `__version__`, còn `build.py` đóng dấu vào `exporterVersion` của
file sinh ra, mà `__init__` thì import `build`. Đọc qua `importlib.metadata` chỉ chạy khi
package đã cài, nên trong repo chưa cài nó im lặng trả về sai.

Trước đây `exporterVersion` là chuỗi `"0.1.0"` gõ cứng và đứng yên qua ba lần phát hành,
tức là nó nói sai chứ không phải nói thiếu.
"""

__version__ = "0.5.6"
