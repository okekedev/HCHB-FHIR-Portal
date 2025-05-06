from dash import html
import dash_bootstrap_components as dbc

def create_navbar():
    """
    Create a navigation bar component.
    
    Returns:
        dash component: A dbc.Navbar component
    """
    return dbc.Navbar(
        dbc.Container(
            [
                # Brand/logo
                html.A(
                    [
                        html.Img(src="/assets/logo.png", height="30px", className="me-2"),
                        dbc.NavbarBrand("Healing Hands Automation", className="ms-2"),
                    ],
                    href="/",
                    style={"textDecoration": "none"},
                ),
                # Navigation links
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Dashboard", href="#", active=True)),
                        dbc.NavItem(dbc.NavLink("Reports", href="#")),
                        dbc.NavItem(dbc.NavLink("Settings", href="#")),
                        dbc.NavItem(dbc.NavLink("Help", href="#")),
                    ],
                    className="ms-auto",
                    navbar=True,
                ),
            ]
        ),
        color="primary",
        dark=True,
        className="mb-4",
    )
