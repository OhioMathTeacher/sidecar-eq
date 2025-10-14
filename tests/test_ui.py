"""Unit tests for UI widgets."""

import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication

from sidecar_eq.ui import IconButton, KnobWidget, QueueTableView, SnapKnobWidget


class TestQueueTableView:
    """Tests for QueueTableView widget."""

    def test_initialization(self, qapp):
        """Test that QueueTableView initializes correctly."""
        view = QueueTableView()
        assert view is not None
        assert hasattr(view, "delete_key_pressed")

    def test_has_delete_signal(self, qapp):
        """Test that delete_key_pressed signal exists."""
        view = QueueTableView()
        # Signal should be connectable
        signal_received = []

        def handler():
            signal_received.append(True)

        view.delete_key_pressed.connect(handler)
        view.delete_key_pressed.emit()
        assert len(signal_received) == 1


class TestIconButton:
    """Tests for IconButton widget."""

    def test_initialization(self, qapp):
        """Test that IconButton initializes with icons."""
        # Use simple color strings as icon paths for testing
        button = IconButton(".", ".", ".", tooltip="Test")
        assert button is not None
        assert button.toolTip() == "Test"
        assert button.isFlat()

    def test_active_state(self, qapp):
        """Test setActive method."""
        button = IconButton(".", ".", ".")
        assert not button._active

        button.setActive(True)
        assert button._active

        button.setActive(False)
        assert not button._active


class TestKnobWidget:
    """Tests for KnobWidget control."""

    def test_initialization(self, qapp):
        """Test that KnobWidget initializes correctly."""
        knob = KnobWidget()
        assert knob is not None
        assert knob.value() == 100  # Default value

    def test_value_setting(self, qapp):
        """Test setValue and value methods."""
        knob = KnobWidget()

        knob.setValue(50)
        assert knob.value() == 50

        knob.setValue(0)
        assert knob.value() == 0

        knob.setValue(100)
        assert knob.value() == 100

    def test_value_clamping(self, qapp):
        """Test that values are clamped to 0-100."""
        knob = KnobWidget()

        knob.setValue(-10)
        assert knob.value() == 0

        knob.setValue(150)
        assert knob.value() == 100

    def test_value_changed_signal(self, qapp):
        """Test that valueChanged signal is emitted."""
        knob = KnobWidget()
        values_received = []

        def handler(value):
            values_received.append(value)

        knob.valueChanged.connect(handler)

        knob.setValue(75)
        assert 75 in values_received

        knob.setValue(25)
        assert 25 in values_received


class TestSnapKnobWidget:
    """Tests for SnapKnobWidget control."""

    def test_initialization(self, qapp):
        """Test that SnapKnobWidget initializes with steps."""
        knob = SnapKnobWidget(steps=3)
        assert knob is not None
        assert knob._steps == 3

    def test_minimum_steps(self, qapp):
        """Test that minimum steps is enforced."""
        knob = SnapKnobWidget(steps=1)
        assert knob._steps >= 2  # Should be clamped to minimum

    def test_value_wrapping(self, qapp):
        """Test that setValue wraps values outside 0-100."""
        knob = SnapKnobWidget(steps=3)

        knob.setValue(150)
        assert 0 <= knob.value() <= 100

        knob.setValue(-50)
        assert 0 <= knob.value() <= 100
