from dash import html
import dash_bootstrap_components as dbc

def create_navbar():
    """
    Create a modern navigation bar component.
    
    Returns:
        dash component: A dbc.Navbar component
    """
    return dbc.Navbar(
        dbc.Container(
            [
                # Brand/logo with improved styling
                html.A(
                    [
                        html.Img(src="/assets/logo.png", height="36px", className="me-2 d-inline-block align-middle"),
                        dbc.NavbarBrand("Healing Hands Automation", className="ms-2 d-inline-block align-middle"),
                    ],
                    href="/",
                    style={"textDecoration": "none"},
                    className="d-flex align-items-center"
                ),
                # Toggle button for mobile view
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                # Navigation links with improved styling
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavItem(dbc.NavLink("Dashboard", href="#", active=True)),
                            dbc.NavItem(dbc.NavLink("Reports", href="#")),
                            dbc.NavItem(dbc.NavLink("Settings", href="#")),
                            dbc.DropdownMenu(
                                [
                                    dbc.DropdownMenuItem("Documentation", href="#"),
                                    dbc.DropdownMenuItem("API Guide", href="#"),
                                    dbc.DropdownMenuItem("Support", href="#"),
                                ],
                                label="Help",
                                nav=True,
                                in_navbar=True,
                                toggle_style={"color": "rgba(255, 255, 255, 0.85)"}
                            ),
                        ],
                        navbar=True,
                        className="ms-auto align-items-center"
                    ),
                    id="navbar-collapse",
                    navbar=True,
                    is_open=False,
                ),
            ],
            fluid=True,
        ),
        color="primary",
        dark=True,
        className="mb-4 py-2 shadow",
        sticky="top",
    )