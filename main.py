import os
import webview

from api import Api


def main():
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    index_path = os.path.join(web_dir, "index.html")

    window = webview.create_window(
        title="OnyProtect",
        url=index_path,
        js_api=Api(),
        width=1280,
        height=800,
        min_size=(960, 640),
        resizable=True,
        confirm_close=False,
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
