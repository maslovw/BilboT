import base64
import json
import logging
from typing import Optional, Tuple, List, Dict
from pydantic import BaseModel, Field
import openai

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "gpt-4o"


class ReceiptItem(BaseModel):
    item: str = Field(..., description="The name of the purchased item")
    price: float = Field(..., description="The price of the item")
    bbox_2d: Optional[Tuple[int, int, int, int]] = Field(
        None, description="Bounding box coordinates for the item in the image (x1, y1, x2, y2)"
    )


class ReceiptData(BaseModel):
    items: List[ReceiptItem] = Field(default_factory=list, description="List of items and their prices")
    purchase_date: Optional[str] = Field(None, description="Purchase date (format: DD.MM.YYYY)")
    purchase_time: Optional[str] = Field(None, description="Purchase time (format: HH:MM:SS)")
    store: Optional[str] = Field(None, description="Name of the store")
    payment_method: Optional[str] = Field(None, description="Method of payment (cash, card, etc.)")
    total_amount: Optional[float] = Field(None, description="Summary/Total amount paid")
    currency: Optional[str] = Field(None, description="Currency used for the transaction (USD, EUR, etc.)")
    is_valid: Optional[bool] = Field(None, description="Whether the receipt is valid or not")
    total_amount_validated: Optional[bool] = Field(None, description="Whether the total matches sum of items")


class ChatGPTImageProcessor:
    """Process receipt images using the OpenAI ChatGPT vision model."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.system_prompt = (
            "You are a receipt analysis assistant. Analyze receipt images to extract structured data."
        )

    async def process_image(self, image_path: str) -> Optional[ReceiptData]:
        """Analyze an image and return extracted receipt data."""
        try:
            with open(image_path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode("utf-8")

            client = openai.AsyncOpenAI()
            schema = ReceiptData.model_json_schema()

            messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this receipt image and return JSON matching this schema:\n" + json.dumps(schema),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                        },
                    ],
                },
            ]

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            receipt_data = ReceiptData.model_validate_json(content)
            return receipt_data
        except Exception as e:
            logger.error(f"OpenAI processing failed: {e}")
            return None


async def process_receipt_image(image_path: str, model_name: str = DEFAULT_MODEL) -> Optional[Dict]:
    """Helper to process a receipt image and return structured data."""
    processor = ChatGPTImageProcessor(model_name=model_name)
    logger.info(f"Processing image with ChatGPT: {image_path}")
    receipt_data = await processor.process_image(image_path)
    return receipt_data.model_dump() if receipt_data else None


async def cli_main() -> int:
    """Command line interface for testing the ChatGPT processor."""
    import argparse
    import sys
    import asyncio

    parser = argparse.ArgumentParser(description="Process receipt images using ChatGPT")
    parser.add_argument("image_path", help="Path to the receipt image file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="ChatGPT model to use")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    processor = ChatGPTImageProcessor(model_name=args.model)
    receipt_data = await processor.process_image(args.image_path)
    if not receipt_data:
        print("ERROR: Failed to process the receipt image", file=sys.stderr)
        return 1

    result = receipt_data.model_dump()
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Results saved to: {args.output}")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(cli_main()))
