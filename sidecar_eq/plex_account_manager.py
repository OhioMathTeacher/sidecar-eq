"""
Plex Server Manager - Discover and connect to Plex servers on local network.
Uses direct server connection with Home Users (managed accounts), not full Plex accounts.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QGroupBox, QFormLayout, QDialogButtonBox, QComboBox,
    QCheckBox, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal

try:
    from plexapi.server import PlexServer
    from plexapi.gdm import GDM
    PLEX_AVAILABLE = True
except ImportError:
    PLEX_AVAILABLE = False


class PlexDiscoveryThread(QThread):
    """Background thread for discovering Plex servers on local network."""
    
    servers_found = Signal(list)  # Emits list of discovered servers
    
    def run(self):
        """Scan local network for Plex servers using GDM."""
        if not PLEX_AVAILABLE:
            self.servers_found.emit([])
            return
            
        try:
            gdm = GDM()
            gdm.scan()
            servers = []
            
            for entry in gdm.entries:
                servers.append({
                    'name': entry.get('Name', 'Unknown Server'),
                    'host': entry.get('host', ''),
                    'port': entry.get('port', '32400'),
                    'uri': entry.get('uri', ''),
                    'token': entry.get('accessToken') or entry.get('token'),
                })
                
            self.servers_found.emit(servers)
        except Exception as e:
            print(f"Plex discovery error: {e}")
            self.servers_found.emit([])


class PlexServerManagerDialog(QDialog):
    """Dialog for managing Plex server connections with Home Users."""
    
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Plex Server Manager")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        
        self.discovery_thread = None
        
        self._init_ui()
        self._load_servers()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Connect to Plex servers on your local network")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        
        # List of configured servers
        list_group = QGroupBox("Configured Plex Servers")
        list_layout = QVBoxLayout(list_group)
        
        self.server_list = QListWidget()
        self.server_list.itemSelectionChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self.server_list)
        
        # Buttons for list management
        list_button_layout = QHBoxLayout()
        self.configure_btn = QPushButton("Configure Users...")
        self.configure_btn.clicked.connect(self._configure_server_users)
        self.configure_btn.setEnabled(False)
        list_button_layout.addWidget(self.configure_btn)
        
        self.remove_btn = QPushButton("Remove Server")
        self.remove_btn.clicked.connect(self._remove_server)
        self.remove_btn.setEnabled(False)
        list_button_layout.addWidget(self.remove_btn)
        list_button_layout.addStretch()
        list_layout.addLayout(list_button_layout)
        
        layout.addWidget(list_group)
        
        # Add server section
        add_group = QGroupBox("Add Plex Server")
        add_layout = QVBoxLayout(add_group)
        
        # Auto-discovery
        discover_layout = QHBoxLayout()
        discover_label = QLabel("🔍 Auto-discover servers on local network:")
        discover_layout.addWidget(discover_label)
        self.discover_btn = QPushButton("Scan Network")
        self.discover_btn.clicked.connect(self._start_discovery)
        self.discover_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        discover_layout.addWidget(self.discover_btn)
        discover_layout.addStretch()
        add_layout.addLayout(discover_layout)
        
        # Manual entry
        manual_form = QFormLayout()
        
        self.server_ip_input = QLineEdit()
        self.server_ip_input.setPlaceholderText("192.168.1.100")
        manual_form.addRow("Or enter server IP:", self.server_ip_input)
        
        self.server_port_input = QLineEdit()
        self.server_port_input.setText("32400")
        self.server_port_input.setMaximumWidth(100)
        manual_form.addRow("Port:", self.server_port_input)
        
        self.server_token_input = QLineEdit()
        self.server_token_input.setPlaceholderText("Optional access token for auto user discovery")
        manual_form.addRow("Token:", self.server_token_input)

        manual_button_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect to Server")
        self.connect_btn.clicked.connect(self._connect_manual)
        self.connect_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        manual_button_layout.addStretch()
        manual_button_layout.addWidget(self.connect_btn)
        manual_form.addRow("", manual_button_layout)
        
        add_layout.addLayout(manual_form)
        layout.addWidget(add_group)
        
        # Info text
        info = QLabel(
            "💡 Tip: Plex servers are discovered automatically on your local network. "
            "No Plex account login required! You'll select which Home Users (managed accounts) "
            "to enable after connecting to a server."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 10px; font-size: 11px;")
        layout.addWidget(info)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def _load_servers(self):
        """Load configured servers from store."""
        servers = self.store.get_record("plex_servers") or []
        
        self.server_list.clear()
        for server in servers:
            server_name = server.get('name', 'Unknown')
            host = server.get('host', '')
            port = server.get('port', '32400')
            users = server.get('users', [])
            user_count = len(users)
            
            extra = " • token saved" if server.get('token') else ''
            item_text = f"🎬 {server_name} ({host}:{port}) - {user_count} user(s){extra}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, server)
            self.server_list.addItem(item)
            
    def _on_selection_changed(self):
        """Handle selection change in server list."""
        has_selection = len(self.server_list.selectedItems()) > 0
        self.configure_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
        
    def _start_discovery(self):
        """Start background network scan for Plex servers."""
        if not PLEX_AVAILABLE:
            QMessageBox.warning(
                self,
                "Plex Not Available",
                "PlexAPI is not installed. Please install it with:\npip install plexapi"
            )
            return
            
        # Disable button during scan
        self.discover_btn.setEnabled(False)
        self.discover_btn.setText("Scanning...")
        
        # Start discovery thread
        self.discovery_thread = PlexDiscoveryThread()
        self.discovery_thread.servers_found.connect(self._on_servers_discovered)
        self.discovery_thread.finished.connect(lambda: self.discover_btn.setEnabled(True))
        self.discovery_thread.finished.connect(lambda: self.discover_btn.setText("Scan Network"))
        self.discovery_thread.start()
        
    def _on_servers_discovered(self, servers):
        """Handle discovered servers."""
        if not servers:
            QMessageBox.information(
                self,
                "No Servers Found",
                "No Plex servers found on your local network.\n\n"
                "Make sure your Plex server is running and accessible."
            )
            return
            
        # Show selection dialog
        dialog = PlexServerDiscoveryDialog(servers, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_server = dialog.get_selected_server()
            if selected_server:
                self._connect_to_server(
                    selected_server['host'],
                    selected_server['port'],
                    selected_server['name'],
                    selected_server.get('token')
                )
                
    def _connect_manual(self):
        """Connect to manually entered server."""
        if not PLEX_AVAILABLE:
            QMessageBox.warning(
                self,
                "Plex Not Available",
                "PlexAPI is not installed. Please install it with:\npip install plexapi"
            )
            return
            
        host = self.server_ip_input.text().strip()
        port = self.server_port_input.text().strip()
        
        if not host:
            QMessageBox.warning(
                self,
                "Missing IP Address",
                "Please enter the server IP address."
            )
            return
        
        token = self.server_token_input.text().strip() or None
        self._connect_to_server(host, port, token=token)
        
    def _connect_to_server(self, host, port, server_name=None, token=None):
        """Connect to Plex server and configure Home Users."""
        try:
            baseurl = f"http://{host}:{port}"

            discovered_name = server_name or "Unknown Server"
            resolved_token = token

            try:
                server = PlexServer(
                    baseurl,
                    token=token,
                    timeout=5,
                ) if token else PlexServer(baseurl, timeout=5)
                discovered_name = getattr(server, "friendlyName", discovered_name)
                if not resolved_token:
                    resolved_token = getattr(server, "_token", None)
            except Exception as exc:
                print(f"Plex quick connect failed for {host}:{port}: {exc}")

            dialog = PlexHomeUserDialog(
                host,
                port,
                discovered_name,
                self.store,
                self,
                admin_token=resolved_token,
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Reload server list
                self._load_servers()
                
                # Clear inputs
                self.server_ip_input.clear()
                self.server_token_input.clear()
                
                QMessageBox.information(
                    self,
                    "Server Added! 🎉",
                    f"Successfully connected to {discovered_name}!\n\n"
                    "This server will now appear in your source dropdown."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Connection Failed",
                f"Failed to connect to Plex server:\n\n{str(e)}\n\n"
                "Please check the IP address and make sure the server is running."
            )
            
    def _configure_server_users(self):
        """Configure Home Users for selected server."""
        selected_items = self.server_list.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        server = item.data(Qt.ItemDataRole.UserRole)
        
        # Open user configuration dialog
        dialog = PlexHomeUserDialog(
            server['host'],
            server['port'],
            server['name'],
            self.store,
            self,
            existing_server=server,
            admin_token=server.get('token')
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_servers()
    
    def _remove_server(self):
        """Remove selected server."""
        selected_items = self.server_list.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        server = item.data(Qt.ItemDataRole.UserRole)
        
        server_name = server.get('name', 'Unknown')
        
        reply = QMessageBox.question(
            self,
            "Remove Server?",
            f"Remove {server_name} and all its configured users?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from store
            servers = self.store.get_record("plex_servers") or []
            servers = [s for s in servers if s.get('name') != server_name]
            self.store.put_record("plex_servers", servers)
            
            # Reload display
            self._load_servers()
            
            QMessageBox.information(
                self,
                "Server Removed",
                f"Removed {server_name} from configured servers."
            )


class PlexServerDiscoveryDialog(QDialog):
    """Dialog for selecting from auto-discovered Plex servers."""
    
    def __init__(self, servers: list, parent=None):
        super().__init__(parent)
        self.servers = servers
        self.selected_server = None
        
        self.setWindowTitle("Discovered Plex Servers")
        self.setMinimumWidth(500)
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"Found {len(self.servers)} Plex server(s) on your network:")
        header.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        
        # Server list
        self.server_list = QListWidget()
        for server in self.servers:
            name = server.get('name', 'Unknown')
            host = server.get('host', '')
            port = server.get('port', '32400')
            
            item_text = f"🎬 {name} ({host}:{port})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, server)
            self.server_list.addItem(item)
            
        self.server_list.setCurrentRow(0)
        layout.addWidget(self.server_list)
        
        # Info
        info = QLabel("Select a server to configure its Home Users.")
        info.setStyleSheet("color: #666; padding: 10px; font-size: 11px;")
        layout.addWidget(info)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_selected_server(self):
        """Get the selected server information."""
        selected_items = self.server_list.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.ItemDataRole.UserRole)
        return None


class PlexHomeUserDialog(QDialog):
    """Dialog for configuring Plex Home Users (managed accounts) for a server."""
    
    def __init__(
        self,
        host: str,
        port: str,
        server_name: str,
        store,
        parent=None,
        existing_server=None,
        admin_token: str | None = None,
    ):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.server_name = server_name
        self.store = store
        self.existing_server = existing_server or {}
        self.admin_token = admin_token or self.existing_server.get("token")
        
        self.setWindowTitle(f"Configure Users for {server_name}")
        self.setMinimumWidth(620)
        self.setMinimumHeight(420)
        
        self.user_widgets = []
        self._discovered_users = []
        
        self._init_ui()
        self._load_home_users()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"Select which Home Users to enable for {self.server_name}")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        
        # Info
        info = QLabel(
            "Home Users are managed accounts on your Plex server. "
            "Enable users you want to access in SidecarEQ, and optionally enter their PINs."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 10px; font-size: 11px;")
        layout.addWidget(info)
        
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666; padding: 0 10px; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # User list area
        self.user_group = QGroupBox("Available Home Users")
        self.user_layout = QVBoxLayout(self.user_group)
        layout.addWidget(self.user_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_configuration)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def _reset_user_layout(self):
        """Remove all widgets from the user layout."""
        while self.user_layout.count():
            item = self.user_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
    
    def _load_home_users(self):
        """Load Home Users from the Plex server."""
        self._reset_user_layout()
        self.user_widgets = []
        existing_users = self.existing_server.get("users", [])

        if not PLEX_AVAILABLE:
            self.status_label.setText(
                "PlexAPI is not installed. Install it to auto-detect Home Users, or add users manually."
            )
            self._create_manual_user_ui(existing_users)
            return

        discovered_users, error_message = self._fetch_home_users()
        if discovered_users:
            self._discovered_users = discovered_users
            self.status_label.setText(
                f"Found {len(discovered_users)} user(s) on {self.server_name}. Enable the profiles you want SidecarEQ to use."
            )
            self._populate_discovered_users(discovered_users, existing_users)
            return

        # Auto detection failed – fall back to manual configuration.
        fallback_message = error_message or "Auto-discovery unavailable. Enter usernames manually."
        self.status_label.setText(fallback_message)
        self._create_manual_user_ui(existing_users)
    
    def _fetch_home_users(self):
        """Attempt to discover Home Users using the provided admin token."""
        if not self.admin_token:
            return None, "No Plex access token available. Add your server token to enable auto-discovery."

        baseurl = f"http://{self.host}:{self.port}"
        try:
            server = PlexServer(baseurl, token=self.admin_token, timeout=10)
            account = server.myPlexAccount()
            system_accounts = {acc.id: acc for acc in server.systemAccounts()}
            plex_users = {user.id: user for user in account.users()}

            discovered = []
            for account_id, system_account in system_accounts.items():
                user_meta = plex_users.get(account_id)
                if user_meta is None:
                    # Skip friend shares that aren't part of Plex Home
                    continue
                requires_pin = bool(getattr(user_meta, "protected", False))
                display_name = user_meta.title or system_account.name
                discovered.append({
                    "id": account_id,
                    "username": system_account.name,
                    "display_name": display_name,
                    "thumb": user_meta.thumb or system_account.thumb,
                    "requires_pin": requires_pin,
                })

            if not discovered:
                return None, "No Plex Home Users were returned for this server."
            return discovered, None

        except Exception as exc:
            print(f"Failed to auto-discover Plex users for {self.server_name}: {exc}")
            return None, f"Automatic discovery failed: {exc}. Enter users manually."

    def _populate_discovered_users(self, users: list, existing_users: list):
        """Render UI rows for discovered users."""
        existing_lookup = {u.get("username"): u for u in existing_users}

        for user_info in users:
            existing = existing_lookup.get(user_info["username"], {})
            self._add_discovered_user_row(user_info, existing)

        add_custom_btn = QPushButton("+ Add Custom User")
        add_custom_btn.clicked.connect(lambda: self._add_user_row({}))
        self.user_layout.addWidget(add_custom_btn)
            
    def _create_manual_user_ui(self, existing_users: list):
        """Create UI for manual user configuration."""
        users = existing_users or [{'username': '', 'pin': '', 'enabled': False}]

        for user_data in users:
            self._add_user_row(user_data)

        add_user_btn = QPushButton("+ Add Another User")
        add_user_btn.clicked.connect(lambda: self._add_user_row({}))
        self.user_layout.addWidget(add_user_btn)

    def _add_discovered_user_row(self, user_info: dict, existing: dict):
        """Add a read-only row for an auto-discovered Plex Home user."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        enabled_cb = QCheckBox()
        enabled_cb.setChecked(existing.get('enabled', True))
        row_layout.addWidget(enabled_cb)

        name_label = QLabel(user_info.get('display_name') or user_info.get('username', 'Unknown'))
        name_label.setMinimumWidth(180)
        name_label.setStyleSheet("font-weight: bold;")
        row_layout.addWidget(name_label)

        pin_input = QLineEdit()
        pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        pin_input.setMaxLength(4)
        pin_input.setMaximumWidth(90)
        pin_input.setText(existing.get('pin', ''))
        requires_pin = bool(user_info.get('requires_pin'))
        placeholder = "PIN required" if requires_pin else "PIN (optional)"
        pin_input.setPlaceholderText(placeholder)
        row_layout.addWidget(pin_input)

        if requires_pin:
            hint_label = QLabel("Requires PIN")
            hint_label.setStyleSheet("color: #a94442;")
        else:
            hint_label = QLabel("No PIN needed")
            hint_label.setStyleSheet("color: #2d7a46;")
        row_layout.addWidget(hint_label)

        row_layout.addStretch()

        self.user_layout.addWidget(row_widget)
        self.user_widgets.append({
            'widget': row_widget,
            'enabled': enabled_cb,
            'username': user_info.get('username'),
            'display_name': user_info.get('display_name'),
            'pin': pin_input,
            'requires_pin': requires_pin,
            'user_id': user_info.get('id'),
            'thumb': user_info.get('thumb'),
            'source': 'auto',
        })
        
    def _add_user_row(self, user_data):
        """Add a user configuration row."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        # Enable checkbox
        enabled_cb = QCheckBox()
        enabled_cb.setChecked(user_data.get('enabled', False))
        row_layout.addWidget(enabled_cb)
        
        # Username
        username_label = QLabel("Username:")
        row_layout.addWidget(username_label)
        username_input = QLineEdit()
        username_input.setText(user_data.get('username', ''))
        username_input.setPlaceholderText("e.g., MusicMan or Billy_Nimbus")
        row_layout.addWidget(username_input)
        
        # PIN
        pin_label = QLabel("PIN (optional):")
        row_layout.addWidget(pin_label)
        pin_input = QLineEdit()
        pin_input.setText(user_data.get('pin', ''))
        pin_input.setPlaceholderText("4-digit PIN")
        pin_input.setMaxLength(4)
        pin_input.setMaximumWidth(80)
        pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        row_layout.addWidget(pin_input)
        
        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setMaximumWidth(30)
        remove_btn.clicked.connect(lambda: self._remove_user_row(row_widget))
        row_layout.addWidget(remove_btn)
        
        self.user_layout.insertWidget(len(self.user_widgets), row_widget)
        self.user_widgets.append({
            'widget': row_widget,
            'enabled': enabled_cb,
            'username': username_input,
            'pin': pin_input,
            'requires_pin': bool(user_data.get('requires_pin', False)),
            'display_name': user_data.get('display_name'),
            'user_id': user_data.get('id'),
            'thumb': user_data.get('thumb'),
            'source': 'manual',
        })
        
    def _remove_user_row(self, widget):
        """Remove a user configuration row."""
        self.user_widgets = [u for u in self.user_widgets if u['widget'] != widget]
        widget.deleteLater()
        
    def _save_configuration(self):
        """Save the user configuration."""
        users = []
        missing_pins = []
        missing_usernames = False

        for user_widget in self.user_widgets:
            if not user_widget['enabled'].isChecked():
                continue

            username_field = user_widget['username']
            if isinstance(username_field, QLineEdit):
                username = username_field.text().strip()
            else:
                username = (username_field or '').strip()

            pin_field = user_widget.get('pin')
            pin = pin_field.text().strip() if isinstance(pin_field, QLineEdit) else str(pin_field or '').strip()

            if not username:
                missing_usernames = True
                continue

            if user_widget.get('requires_pin') and not pin:
                missing_pins.append(username)
                continue

            user_entry = {
                'username': username,
                'pin': pin,
                'enabled': True,
            }

            if user_widget.get('display_name'):
                user_entry['display_name'] = user_widget['display_name']
            if user_widget.get('user_id'):
                user_entry['id'] = user_widget['user_id']
            if user_widget.get('thumb'):
                user_entry['thumb'] = user_widget['thumb']
            if 'requires_pin' in user_widget:
                user_entry['requires_pin'] = bool(user_widget['requires_pin'])

            users.append(user_entry)

        if missing_usernames and not users:
            QMessageBox.warning(
                self,
                "Missing Username",
                "Please enter a username for each enabled entry."
            )
            return

        if missing_pins:
            QMessageBox.warning(
                self,
                "PIN Required",
                "Enter the 4-digit PIN for: {}".format(
                    ", ".join(missing_pins)
                )
            )
            return

        if not users:
            QMessageBox.warning(
                self,
                "No Users Enabled",
                "Please enable at least one user with a username."
            )
            return
            
        # Save server configuration
        servers = self.store.get_record("plex_servers") or []
        
        # Remove existing entry for this server if editing
        servers = [s for s in servers if s.get('name') != self.server_name]
        
        # Add new configuration
        server_config = {
            'name': self.server_name,
            'host': self.host,
            'port': self.port,
            'users': users,
            'token': self.admin_token,
        }
        servers.append(server_config)
        
        self.store.put_record("plex_servers", servers)
        
        self.accept()


class PlexAccountSelectorDialog(QDialog):
    """Simple dialog to select which Plex Home User to browse as."""
    
    def __init__(self, server_name: str, users: list, parent=None):
        super().__init__(parent)
        self.server_name = server_name
        self.users = users
        self.selected_user = None
        
        self.setWindowTitle(f"Connect to {server_name}")
        self.setMinimumWidth(400)
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Select which user to connect as:")
        header.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        
        # User selector
        self.user_combo = QComboBox()
        for user in self.users:
            display_name = user.get('display_name') or user.get('username', 'Unknown')
            has_pin = '🔒' if user.get('requires_pin') or user.get('pin') else '👤'
            self.user_combo.addItem(f"{has_pin} {display_name}", user)
        layout.addWidget(self.user_combo)
        
        # PIN input (shown only if user has PIN)
        self.pin_widget = QWidget()
        pin_layout = QHBoxLayout(self.pin_widget)
        pin_layout.setContentsMargins(0, 10, 0, 0)
        pin_label = QLabel("PIN:")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setPlaceholderText("Enter 4-digit PIN")
        self.pin_input.setMaxLength(4)
        pin_layout.addWidget(pin_label)
        pin_layout.addWidget(self.pin_input)
        layout.addWidget(self.pin_widget)
        
        # Connect combo change to PIN visibility
        self.user_combo.currentIndexChanged.connect(self._update_pin_visibility)
        self._update_pin_visibility()
        
        # Info
        info = QLabel(
            "Each user may have access to different libraries and content."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 10px; font-size: 11px;")
        layout.addWidget(info)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def _update_pin_visibility(self):
        """Show/hide PIN input based on selected user."""
        user = self.get_selected_user()
        if user and (user.get('requires_pin') or user.get('pin')):
            self.pin_widget.setVisible(True)
            stored_pin = user.get('pin') or ''
            if stored_pin and not self.pin_input.text():
                self.pin_input.setText(stored_pin)
        else:
            self.pin_widget.setVisible(False)
            self.pin_input.clear()
            
    def _validate_and_accept(self):
        """Validate PIN if needed before accepting."""
        user = self.get_selected_user()
        if user and (user.get('requires_pin') or user.get('pin')):
            entered_pin = self.pin_input.text().strip()
            if not entered_pin and user.get('requires_pin'):
                QMessageBox.warning(
                    self,
                    "PIN Required",
                    "This Plex user requires a PIN."
                )
                return
            if entered_pin:
                user['pin'] = entered_pin
        self.accept()
        
    def get_selected_user(self):
        """Get the selected user information."""
        index = self.user_combo.currentIndex()
        if index >= 0:
            return self.user_combo.itemData(index)
        return None

