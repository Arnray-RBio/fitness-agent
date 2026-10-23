from ollama import Client
from pydantic import BaseModel


class VenueInfo(BaseModel):
    name: str
    services: list[str]
    monthly_membership_sgd: float | None


# Fictional example, not a real venue.
source_text = """
Example Recovery is a recovery centre in Singapore.
It offers cold plunge sessions and an infrared sauna.
Contact the centre for membership prices.
"""


def main():
    client = Client(
        host="http://localhost:11434",
        timeout=300,
    )

    print(
        "Connecting to Ollama. The first response may take a while...",
        flush=True,
    )

    response = client.chat(
        model="qwen3.5:4b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract venue information only from the supplied text. "
                    "Do not invent details. Use null for an unstated price. "
                    "Return JSON matching the supplied schema."
                ),
            },
            {"role": "user", "content": source_text},
        ],
        format=VenueInfo.model_json_schema(),
        think=False,
        options={
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 256,
        },
        stream=False,
    )

    venue = VenueInfo.model_validate_json(response.message.content)
    print(venue.model_dump_json(indent=2))


if __name__ == "__main__":
    main()