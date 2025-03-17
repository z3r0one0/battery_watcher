import ctypes
import time
import wmi
from winotify import Notification, audio

# Configuration
CHECK_INTERVAL = 180  # 3 minutes in seconds
LOW_BATTERY_THRESHOLD = 50
FULL_BATTERY_THRESHOLD = 100

# Initialize Windows-specific components - but only when not in test mode
wmi_connection = None

def initialize_wmi():
    """Initialize the WMI connection if not already initialized"""
    global wmi_connection
    if wmi_connection is None:
        wmi_connection = wmi.WMI()
    return wmi_connection

def get_battery_status():
    """Get battery status using Windows Management Instrumentation (WMI)"""
    try:
        # Get a fresh WMI connection each time
        conn = initialize_wmi()
        batteries = conn.Win32_Battery()
        if batteries:
            battery = batteries[0]
            percent = battery.EstimatedChargeRemaining
            power_plugged = battery.BatteryStatus == 2  # 2 means AC power
            return percent, power_plugged
        return None, None
    except Exception as e:
        print(f"Error getting battery status: {e}")
        return None, None

def notify(title, message, is_urgent=False):
    """Show Windows 11 toast notification"""
    notification = Notification(
        app_id="Battery Monitor",
        title=title,
        msg=message,
        duration="short"  # "short" or "long"
    )
    
    # Add sound for urgent notifications
    if is_urgent:
        notification.set_audio(audio.Default, loop=False)
    
    notification.show()

def prevent_sleep_during_notification():
    """Prevent system from sleeping during notification"""
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)  # ES_SYSTEM_REQUIRED | ES_CONTINUOUS

def allow_sleep():
    """Allow system to sleep normally"""
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # ES_CONTINUOUS

def main(test_mode=False, max_iterations=None):
    """
    Main function to monitor battery status
    
    Args:
        test_mode: If True, enables test mode for unit testing
        max_iterations: Maximum number of loop iterations (for testing)
    """
    last_notification_type = None
    iteration_count = 0
    
    print("Battery monitor started. Press Ctrl+C to exit.")
    print(f"Checking battery every {CHECK_INTERVAL//60} minutes.")
    
    while True:
        try:
            # For testing, we can limit the number of iterations
            if test_mode and max_iterations is not None:
                iteration_count += 1
                if iteration_count > max_iterations:
                    break
                    
            percent, power_plugged = get_battery_status()
            
            if percent is None:
                print("Could not get battery information")
                if not test_mode:
                    time.sleep(CHECK_INTERVAL)
                continue
                
            status_text = "Plugged In" if power_plugged else "Not Plugged In"
            print(f"Battery: {percent}% ({status_text})")
            
            # Alert when battery is low and not charging
            if percent <= LOW_BATTERY_THRESHOLD and not power_plugged and last_notification_type != "low":
                prevent_sleep_during_notification()
                notify(
                    "Low Battery",
                    f"Battery at {percent}%. Please connect charger.",
                    is_urgent=True
                )
                last_notification_type = "low"
                allow_sleep()
                
            # Alert when battery is full and still charging
            elif percent >= FULL_BATTERY_THRESHOLD and power_plugged and last_notification_type != "full":
                prevent_sleep_during_notification()
                notify(
                    "Battery Full",
                    f"Battery at {percent}%. You can disconnect charger."
                )
                last_notification_type = "full"
                allow_sleep()
            
            # Reset notification state when between thresholds
            elif LOW_BATTERY_THRESHOLD < percent < FULL_BATTERY_THRESHOLD:
                last_notification_type = None
            
            # Skip sleep in test mode
            if not test_mode:
                time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("Battery monitor stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            if not test_mode:
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()