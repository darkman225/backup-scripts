import time

def is_modified_older_than_days(modified_at_epoch: int, days: int) -> bool:
    """
    Check if the modified_at_epoch is older than the specified number of days.
    """
    if days < 0:
        raise ValueError("Days must be a non-negative integer.")
    
    now_epoch = int(time.time())
    
    # print(f"Current epoch time: {now_epoch}, Modified at epoch time: {modified_at_epoch}, Days: {days}")
  
    return (now_epoch - modified_at_epoch) > days * 24 * 60 * 60
