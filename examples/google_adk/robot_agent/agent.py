import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

def get_current_inventory() -> dict:
    """Retrieves the currently avilable items.

    Returns:
        dict: status and result or error msg.
    """
    # get Image from robot and process.
    json = {'items': '4 blocks avilable'}
    if json is not None:
        return {
            "status": "success",
            "report": "4 blocks avilable",
        }
    else:
        return {
            "status": "error",
            "error_message": f"items not available.",
        }


def pick_item(item: str) -> dict:
    """Robot pick up the item and put in tray for pickup.

    Args:
        item (str): The ID of item to be picked up.

    Returns:
        dict: status and result or error msg.
    """
    # send commadn to robot to pick item.
    task_done = True
    if task_done:
        return {"status": "success"}
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, Couldn't complete pick."
            ),
        }

def handoff_to_teleoperator(item: str) -> dict:
    """If Robot is unbale to pick up the item, this will handoff the customer requests to leleoperator to control robot and pick the item.

    Args:
        item (str): The ID of item to be picked up.

    Returns:
        dict: status and result or error msg.
    """
    # send commadn to robot to pick item.
    task_done = True
    if task_done:
        return {"status": "success"}
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, Couldn't complete pick."
            ),
        }


root_agent = Agent(
    name="robot_store",
    model="gemini-2.0-flash",
    description=(
        "Agent to act as shop keeper, the shop has mobile robot, Agent handles the customer request and sends command to robot ."
    ),
    instruction=(
        "You are a helpful agent who acts as shop keeper for Robot managed store, you enquire customer what items he need, and ask robot to pack the items user asked. To get currently avilable item, ask robot 'get_current_inventory', 'pick_item' with the item ID to pick functions." \
        "If robot is unable to pick the item, you can handoff the request to teleoperator by calling 'handoff_to_teleoperator' with the item ID. If you are not sure about the item, ask customer for more details." \
        "If you are not sure about the item, ask customer for more details. If you are not able to understand the request, ask customer to rephrase the request."
    ),
    tools=[get_current_inventory, pick_item, handoff_to_teleoperator],
)
