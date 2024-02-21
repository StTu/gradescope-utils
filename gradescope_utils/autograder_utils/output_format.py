from PIL import Image
import base64
from io import BytesIO


def image_to_html(image: Image) -> str:
    """Converts an image to an HTML string.

    Args:
        image: The image to convert.

    Returns:
        The HTML string.
    """

    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f'<img src="data:image/jpeg;base64,{img_str}" />'
