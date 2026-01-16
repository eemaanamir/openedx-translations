from __future__ import annotations

import os
import typing as t
from glob import glob

import importlib_resources
from tutor import hooks
from tutor.__about__ import __version_suffix__
from tutormfe.hooks import PLUGIN_SLOTS

from .__about__ import __version__

# Handle version suffix in main mode, just like tutor core
if __version_suffix__:
    __version__ += "-" + __version_suffix__


################# Configuration
config: t.Dict[str, t.Dict[str, t.Any]] = {
    # Add here your new settings
    "defaults": {
        "VERSION": __version__,
        "WELCOME_MESSAGE": "Join the Wikimedia learning community",
        "PRIMARY_COLOR": "#0E65C0",  # Indigo
        "ENABLE_DARK_TOGGLE": True,
        # Footer links are dictionaries with a "title" and "url"
        # To remove all links, run:
        # tutor config save --set INDIGO_FOOTER_NAV_LINKS=[]
        "FOOTER_NAV_LINKS": [
            {"title": "Privacy Policy", "url": "https://wikimediafoundation.org/privacy-policy/"},
            {"title": "Edly Privacy Policy", "url": "https://edly.io/euserpp/"},
        ],
    },
    "unique": {},
    "overrides": {},
}

# Theme templates
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    str(importlib_resources.files("tutorindigo") / "templates")
)
# This is where the theme is rendered in the openedx build directory
hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    [
        ("indigo", "build/openedx/themes"),
        ("indigo/env.config.jsx", "plugins/mfe/build/mfe"),
    ],
)

# Force the rendering of scss files, even though they are included in a "partials" directory
hooks.Filters.ENV_PATTERNS_INCLUDE.add_items(
    [
        r"indigo/lms/static/sass/partials/lms/theme/",
        r"indigo/cms/static/sass/partials/cms/theme/",
    ]
)


# init script: set theme automatically
with open(
    os.path.join(
        str(importlib_resources.files("tutorindigo") / "templates"),
        "indigo",
        "tasks",
        "init.sh",
    ),
    encoding="utf-8",
) as task_file:
    hooks.Filters.CLI_DO_INIT_TASKS.add_item(("lms", task_file.read()))


# Override openedx & mfe docker image names
@hooks.Filters.CONFIG_DEFAULTS.add(priority=hooks.priorities.LOW)
def _override_openedx_docker_image(
    items: list[tuple[str, t.Any]],
) -> list[tuple[str, t.Any]]:
    openedx_image = ""
    mfe_image = ""
    for k, v in items:
        if k == "DOCKER_IMAGE_OPENEDX":
            openedx_image = v
        elif k == "MFE_DOCKER_IMAGE":
            mfe_image = v
    if openedx_image:
        items.append(("DOCKER_IMAGE_OPENEDX", f"{openedx_image}-indigo"))
    if mfe_image:
        items.append(("MFE_DOCKER_IMAGE", f"{mfe_image}-indigo"))
    return items


# Load all configuration entries
hooks.Filters.CONFIG_DEFAULTS.add_items(
    [(f"INDIGO_{key}", value) for key, value in config["defaults"].items()]
)
hooks.Filters.CONFIG_UNIQUE.add_items(
    [(f"INDIGO_{key}", value) for key, value in config["unique"].items()]
)
hooks.Filters.CONFIG_OVERRIDES.add_items(list(config["overrides"].items()))


#  MFEs that are styled using Indigo
indigo_styled_mfes = [
    "learning",
    "learner-dashboard",
    "profile",
    "account",
    "discussions",
    "messenger",
    "communications",
]


for mfe in indigo_styled_mfes:
    hooks.Filters.ENV_PATCHES.add_items(
        [
            (
                f"mfe-dockerfile-post-npm-install-{mfe}",
                """
RUN npm install @edly-io/wikimedia-frontend-component-footer@latest
RUN npm install '@edx/brand@npm:@edly-io/indigo-brand-openedx@^2.2.2'
RUN npm install @edx/frontend-plugin-notifications@^2.0.3
""",
            ),
            (
                f"mfe-env-config-runtime-definitions-{mfe}",
                """
const { default: IndigoFooter } = await import('@edly-io/wikimedia-frontend-component-footer');
const { AppContext } = await import ('@edx/frontend-platform/react');
const { useContext } = await import ('react');
const { NotificationsTray } = await import('@edx/frontend-plugin-notifications');
""",
            ),
        ]
    )


hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-dockerfile-post-npm-install-authn",
        "RUN npm install '@edx/brand@npm:@edly-io/indigo-brand-openedx@^2.2.2'",
    )
)

# Include js file in lms main.html, main_django.html, and certificate.html

hooks.Filters.ENV_PATCHES.add_items(
    [
        # for production
        (
            "openedx-common-assets-settings",
            """
javascript_files = ['base_application', 'application', 'certificates_wv']
dark_theme_filepath = ['indigo/js/dark-theme.js']

for filename in javascript_files:
    if filename in PIPELINE['JAVASCRIPT']:
        PIPELINE['JAVASCRIPT'][filename]['source_filenames'] += dark_theme_filepath
""",
        ),
        # for development
        (
            "openedx-lms-development-settings",
            """
javascript_files = ['base_application', 'application', 'certificates_wv']
dark_theme_filepath = ['indigo/js/dark-theme.js']

for filename in javascript_files:
    if filename in PIPELINE['JAVASCRIPT']:
        PIPELINE['JAVASCRIPT'][filename]['source_filenames'] += dark_theme_filepath

MFE_CONFIG['INDIGO_ENABLE_DARK_TOGGLE'] = {{ INDIGO_ENABLE_DARK_TOGGLE }}
MFE_CONFIG['INDIGO_FOOTER_NAV_LINKS'] = {{ INDIGO_FOOTER_NAV_LINKS }}
""",
        ),
        (
            "openedx-lms-production-settings",
            """
MFE_CONFIG['INDIGO_ENABLE_DARK_TOGGLE'] = {{ INDIGO_ENABLE_DARK_TOGGLE }}
MFE_CONFIG['INDIGO_FOOTER_NAV_LINKS'] = {{ INDIGO_FOOTER_NAV_LINKS }}
""",
        ),
    ]
)


# Apply patches from tutor-indigo
for path in glob(
    os.path.join(
        str(importlib_resources.files("tutorindigo") / "patches"),
        "*",
    )
):
    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item((os.path.basename(path), patch_file.read()))


for mfe in indigo_styled_mfes:
    PLUGIN_SLOTS.add_item(
        (
            mfe,
            "footer_slot",
            """
            {
                op: PLUGIN_OPERATIONS.Hide,
                widgetId: 'default_contents',
            },
            {
                op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'default_contents',
                    type: DIRECT_PLUGIN,
                    priority: 1,
                    RenderWidget: <IndigoFooter />,
                },
            },
            {
                op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'read_theme_cookie',
                    type: DIRECT_PLUGIN,
                    priority: 2,
                    RenderWidget: AddDarkTheme,
                },
            },
  """,
        ),
    )

    PLUGIN_SLOTS.add_item(
        (
            mfe,
            "desktop_main_menu_slot",
            """
            {
                op: PLUGIN_OPERATIONS.Hide,
                widgetId: 'default_contents',
            },
            {
              op: PLUGIN_OPERATIONS.Insert,
              widget: {
                id: 'dynamic_tabs',
                type: DIRECT_PLUGIN,
                RenderWidget: () => {
                  const [tabs, setTabs] = React.useState([]);
                  const url = `${getConfig().LMS_BASE_URL}/wikimedia_general/api/v0/lms_tabs`;

                  React.useEffect(() => {
                    getAuthenticatedHttpClient().get(url)
                      .then(response => {
                        if (response?.data?.tabs) {
                          setTabs(response.data.tabs);
                        }
                      })
                      .catch(error => {
                        console.error("Failed to load LMS tabs:", error);
                      });
                  }, []);

                  return (
                    <>
                      {tabs.map(tab => (
                        <a
                          key={tab.id}
                          className="nav-link"
                          href={tab.url}
                        >
                          {tab.name}
                        </a>
                      ))}
                    </>
                  );
                },
              },
            }
            """,
        ),
    )

    PLUGIN_SLOTS.add_item(
        (
            mfe,
            "desktop_secondary_menu_slot",
            """
            {
                op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'language_selector_widget',
                    type: DIRECT_PLUGIN,
                    priority: 9,
                    RenderWidget: LanguageWidgetIntl,
                },
            },
            {
              op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'notification-drawer-widget',
                    priority: 10,
                    type: DIRECT_PLUGIN,
                    RenderWidget: NotificationsTray,
                },
            },
            """
        )
    )

    PLUGIN_SLOTS.add_item(
        (
            mfe,
            "org.openedx.frontend.layout.header_learning_help.v1",
            """
            {
                op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'language_selector_widget',
                    type: DIRECT_PLUGIN,
                    priority: 9,
                    RenderWidget: LanguageWidgetIntl,
                },
            },
            {
                op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'notification-drawer-widget',
                    priority: 10,
                    type: DIRECT_PLUGIN,
                    RenderWidget: NotificationsTray,
                },
            },
            """
        ),
    )
