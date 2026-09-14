import asyncio
import aiohttp

from config import (
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_USER_ID,
    GRAPH_API_VERSION,
)


def api_url(path: str):
    return (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/"
        f"{path.lstrip('/')}"
    )


async def request(
    method,
    path,
    *,
    params=None,
    json_data=None,
):
    timeout = aiohttp.ClientTimeout(
        total=120
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        url = api_url(path)

        if method == "POST":
            async with session.post(
                url,
                params=params,
                json=json_data,
            ) as response:

                data = await response.json(
                    content_type=None
                )

        else:
            async with session.get(
                url,
                params=params,
            ) as response:

                data = await response.json(
                    content_type=None
                )

        if response.status >= 400:
            raise RuntimeError(
                f"Instagram API error "
                f"{response.status}: {data}"
            )

        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(
                f"Instagram API error: {data}"
            )

        return data


async def create_image_container(
    image_url: str,
    caption: str,
):
    if not INSTAGRAM_USER_ID:
        raise RuntimeError(
            "INSTAGRAM_USER_ID is missing."
        )

    if not INSTAGRAM_ACCESS_TOKEN:
        raise RuntimeError(
            "INSTAGRAM_ACCESS_TOKEN is missing."
        )

    data = await request(
        "POST",
        f"{INSTAGRAM_USER_ID}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
    )

    creation_id = data.get(
        "id"
    )

    if not creation_id:
        raise RuntimeError(
            f"No creation ID returned: {data}"
        )

    return creation_id


async def get_container_status(
    creation_id: str,
):
    data = await request(
        "GET",
        creation_id,
        params={
            "fields": "status_code,status",
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
    )

    return data


async def wait_for_container(
    creation_id: str,
    timeout_seconds: int = 180,
):
    elapsed = 0

    while elapsed < timeout_seconds:
        status = await get_container_status(
            creation_id
        )

        status_code = str(
            status.get(
                "status_code",
                ""
            )
        ).upper()

        if status_code in {
            "FINISHED",
            "PUBLISHED",
        }:
            return status

        if status_code in {
            "ERROR",
            "EXPIRED",
        }:
            raise RuntimeError(
                f"Instagram media processing failed: "
                f"{status}"
            )

        await asyncio.sleep(5)

        elapsed += 5

    raise TimeoutError(
        "Instagram media container "
        "processing timed out."
    )


async def publish_container(
    creation_id: str,
):
    data = await request(
        "POST",
        f"{INSTAGRAM_USER_ID}/media_publish",
        params={
            "creation_id": creation_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
    )

    media_id = data.get(
        "id"
    )

    if not media_id:
        raise RuntimeError(
            f"No media ID returned: {data}"
        )

    return media_id


async def publish_image(
    image_url: str,
    caption: str,
):
    creation_id = (
        await create_image_container(
            image_url,
            caption,
        )
    )

    await wait_for_container(
        creation_id
    )

    media_id = (
        await publish_container(
            creation_id
        )
    )

    return {
        "creation_id": creation_id,
        "media_id": media_id,
    }


async def verify_connection():
    if not INSTAGRAM_USER_ID:
        raise RuntimeError(
            "INSTAGRAM_USER_ID is missing."
        )

    if not INSTAGRAM_ACCESS_TOKEN:
        raise RuntimeError(
            "INSTAGRAM_ACCESS_TOKEN is missing."
        )

    data = await request(
        "GET",
        INSTAGRAM_USER_ID,
        params={
            "fields": "id,username",
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
    )

    return data
