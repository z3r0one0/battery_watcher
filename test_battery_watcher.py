import pytest
from unittest.mock import patch, MagicMock
import battery_watcher

@pytest.fixture
def mock_wmi():
    """Fixture to mock WMI connection and battery objects"""
    mock_battery = MagicMock()
    mock_battery.EstimatedChargeRemaining = 75
    mock_battery.BatteryStatus = 1  # Not plugged in
    
    mock_batteries = [mock_battery]
    
    # Create a mock WMI instance
    mock_wmi_instance = MagicMock()
    mock_wmi_instance.Win32_Battery.return_value = mock_batteries
    
    # Patch the initialize_wmi function to return our mock
    with patch('battery_watcher.initialize_wmi', return_value=mock_wmi_instance):
        yield mock_battery

@pytest.fixture
def mock_notification():
    """Fixture to mock Windows notifications"""
    with patch('battery_watcher.Notification') as mock_notif:
        mock_notif_instance = MagicMock()
        mock_notif.return_value = mock_notif_instance
        yield mock_notif

@pytest.fixture
def mock_sleep():
    """Fixture to mock time.sleep to speed up tests"""
    with patch('time.sleep'):
        yield

@pytest.fixture
def mock_ctypes():
    """Fixture to mock ctypes calls for sleep prevention"""
    with patch('ctypes.windll.kernel32.SetThreadExecutionState'):
        yield

class TestBatteryStatus:
    def test_get_battery_status_normal(self, mock_wmi):
        """Test getting battery status under normal conditions"""
        # Set up the mock battery
        mock_wmi.EstimatedChargeRemaining = 75
        mock_wmi.BatteryStatus = 1  # Not plugged in
        
        # Call the function
        percent, power_plugged = battery_watcher.get_battery_status()
        
        # Assert the results
        assert percent == 75
        assert power_plugged is False

    def test_get_battery_status_charging(self, mock_wmi):
        """Test getting battery status when charging"""
        # Set up the mock battery
        mock_wmi.EstimatedChargeRemaining = 60
        mock_wmi.BatteryStatus = 2  # Plugged in
        
        # Call the function
        percent, power_plugged = battery_watcher.get_battery_status()
        
        # Assert the results
        assert percent == 60
        assert power_plugged is True

    def test_get_battery_status_exception(self):
        """Test handling of exceptions in get_battery_status"""
        with patch('battery_watcher.initialize_wmi', side_effect=Exception("Test exception")):
            percent, power_plugged = battery_watcher.get_battery_status()
            assert percent is None
            assert power_plugged is None

    def test_get_battery_status_no_battery(self):
        """Test when no battery is found"""
        # Create a mock WMI instance with no batteries
        mock_wmi_instance = MagicMock()
        mock_wmi_instance.Win32_Battery.return_value = []  # Empty list, no batteries
        
        # Patch the initialize_wmi function
        with patch('battery_watcher.initialize_wmi', return_value=mock_wmi_instance):
            percent, power_plugged = battery_watcher.get_battery_status()
            assert percent is None
            assert power_plugged is None
            
    def test_initialize_wmi(self):
        """Test the initialize_wmi function"""
        # Reset the global wmi_connection to None
        battery_watcher.wmi_connection = None
        
        # Mock the wmi.WMI class
        with patch('wmi.WMI') as mock_wmi:
            # First call should create a new connection
            conn1 = battery_watcher.initialize_wmi()
            assert conn1 is not None
            mock_wmi.assert_called_once()
            
            # Second call should reuse the existing connection
            mock_wmi.reset_mock()
            conn2 = battery_watcher.initialize_wmi()
            assert conn2 is conn1
            mock_wmi.assert_not_called()

class TestNotifications:
    def test_notify_normal(self, mock_notification):
        """Test normal notification without urgency"""
        battery_watcher.notify("Test Title", "Test Message")
        
        # Check if notification was created with correct parameters
        mock_notification.assert_called_once()
        mock_notification.return_value.show.assert_called_once()
        assert not mock_notification.return_value.set_audio.called
        
        # Check the notification parameters
        args, kwargs = mock_notification.call_args
        assert kwargs['title'] == "Test Title"
        assert kwargs['msg'] == "Test Message"

    def test_notify_urgent(self, mock_notification):
        """Test urgent notification with sound"""
        battery_watcher.notify("Test Title", "Test Message", is_urgent=True)
        
        # Check if notification was created with correct parameters and sound
        mock_notification.assert_called_once()
        mock_notification.return_value.show.assert_called_once()
        mock_notification.return_value.set_audio.assert_called_once()
        
        # Check the notification parameters
        args, kwargs = mock_notification.call_args
        assert kwargs['title'] == "Test Title"
        assert kwargs['msg'] == "Test Message"

class TestSleepPrevention:
    def test_prevent_sleep(self, mock_ctypes):
        """Test that prevent_sleep_during_notification calls the correct Windows API"""
        battery_watcher.prevent_sleep_during_notification()
        battery_watcher.ctypes.windll.kernel32.SetThreadExecutionState.assert_called_once_with(0x80000002)

    def test_allow_sleep(self, mock_ctypes):
        """Test that allow_sleep calls the correct Windows API"""
        battery_watcher.allow_sleep()
        battery_watcher.ctypes.windll.kernel32.SetThreadExecutionState.assert_called_once_with(0x80000000)

class TestMainFunction:
    @patch('battery_watcher.get_battery_status')
    def test_main_low_battery(self, mock_get_status, mock_notification, mock_sleep, mock_ctypes):
        """Test main function with low battery scenario"""
        # Set up the mock to return low battery
        battery_level = battery_watcher.LOW_BATTERY_THRESHOLD - 1
        mock_get_status.return_value = (battery_level, False)  # Low battery, not plugged in
        
        # Run the main function in test mode with just 1 iteration
        battery_watcher.main(test_mode=True, max_iterations=1)
        
        # Check if notification was created with correct parameters
        mock_notification.assert_called_once()
        args, kwargs = mock_notification.call_args
        assert kwargs['title'] == "Low Battery"
        assert f"Battery at {battery_level}%" in kwargs['msg']

    @patch('battery_watcher.get_battery_status')
    def test_main_full_battery(self, mock_get_status, mock_notification, mock_sleep, mock_ctypes):
        """Test main function with full battery scenario"""
        # Set up the mock to return full battery
        battery_level = battery_watcher.FULL_BATTERY_THRESHOLD
        mock_get_status.return_value = (battery_level, True)  # Full battery, plugged in
        
        # Run the main function in test mode with just 1 iteration
        battery_watcher.main(test_mode=True, max_iterations=1)
        
        # Check if notification was created with correct parameters
        mock_notification.assert_called_once()
        args, kwargs = mock_notification.call_args
        assert kwargs['title'] == "Battery Full"
        assert f"Battery at {battery_level}%" in kwargs['msg']

    @patch('battery_watcher.get_battery_status')
    def test_main_normal_battery(self, mock_get_status, mock_notification, mock_sleep):
        """Test main function with normal battery level (no notification)"""
        # Set up the mock to return normal battery level
        mock_get_status.return_value = (75, True)  # Normal battery level, plugged in
        
        # Run the main function in test mode with just 1 iteration
        battery_watcher.main(test_mode=True, max_iterations=1)
        
        # Check that no notification was shown
        mock_notification.assert_not_called()

    @patch('battery_watcher.get_battery_status')
    def test_main_exception_handling(self, mock_get_status, mock_sleep):
        """Test main function's exception handling"""
        # Set up the mock to raise an exception
        mock_get_status.side_effect = Exception("Test exception")
        
        # Run the main function in test mode with just 1 iteration
        battery_watcher.main(test_mode=True, max_iterations=1)
        
        # The test passes if no unhandled exception is raised
        
    @patch('battery_watcher.get_battery_status')
    def test_main_no_battery_info(self, mock_get_status, mock_notification, mock_sleep):
        """Test main function when no battery information is available"""
        # Set up the mock to return None for battery info
        mock_get_status.return_value = (None, None)
        
        # Run the main function in test mode with just 1 iteration
        battery_watcher.main(test_mode=True, max_iterations=1)
        
        # Check that no notification was shown
        mock_notification.assert_not_called()
        
    @patch('battery_watcher.get_battery_status')
    def test_main_reset_notification_state(self, mock_get_status, mock_notification, mock_sleep):
        """Test that notification state is reset when battery level is between thresholds"""
        # First iteration: low battery notification
        mock_get_status.side_effect = [
            (battery_watcher.LOW_BATTERY_THRESHOLD - 1, False),  # Low battery, not plugged in
            (75, True)  # Normal battery level, should reset notification state
        ]
        
        # Run the main function in test mode with 2 iterations
        battery_watcher.main(test_mode=True, max_iterations=2)
        
        # Check that notification was shown once
        assert mock_notification.call_count == 1
        
    @patch('battery_watcher.get_battery_status')
    def test_main_keyboard_interrupt(self, mock_get_status):
        """Test that KeyboardInterrupt is handled properly"""
        # Set up the mock to raise KeyboardInterrupt
        mock_get_status.side_effect = KeyboardInterrupt()
        
        # Run the main function - it should exit gracefully
        battery_watcher.main(test_mode=True)
        
        # The test passes if no unhandled exception is raised 