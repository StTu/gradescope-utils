from PIL import Image
import base64
from io import BytesIO


def image_to_html(image: Image, format="jpeg") -> str:
    """Converts an image to an HTML string.

    Args:
        image: The image to convert.

    Returns:
        The HTML string.
    """

    buffered = BytesIO()
    image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f'<img src="data:image/{format};base64,{img_str}" />'
