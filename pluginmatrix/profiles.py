"""Versioned data-only profiles. No config-loaded code or alternate verifier."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VerificationProfile:
    id: str
    revision: int
    timeout: int
    stability_window: int
    suggest_registrations: bool
    minimum_environments: int = 1
    maximum_environments: int = 256
    fixed_builds: bool = False
    complete_analysis: bool = False

    def to_dict(self):
        return asdict(self)


# Revisions are immutable contracts. Extend this registry in source, not via
# import paths or expressions in user configuration.
PROFILES = (
    VerificationProfile('quick', 1, 120, 5, False, maximum_environments=1),
    VerificationProfile('standard', 1, 180, 10, True, maximum_environments=1),
    VerificationProfile('matrix', 1, 180, 10, True, minimum_environments=2),
    VerificationProfile('strict', 1, 240, 30, True, fixed_builds=True, complete_analysis=True),
)


def resolve_profile(value) -> VerificationProfile | None:
    if value is None:
        return None
    if isinstance(value, VerificationProfile):
        value = {'id': value.id, 'revision': value.revision}
    if isinstance(value, str):
        value = {'id': value, 'revision': 1}
    if (not isinstance(value, dict) or set(value) != {'id', 'revision'}
            or type(value['revision']) is not int):
        raise ValueError('profile requires id and integer revision')
    for profile in PROFILES:
        if (profile.id, profile.revision) == (value['id'], value['revision']):
            return profile
    raise ValueError(f'unknown profile/revision: {value!r}; use quick, standard, matrix or strict revision 1')


def profile_reference(profile):
    return {'id': profile.id, 'revision': profile.revision} if profile else None


def validate_profile(profile, environments, stability):
    if profile is None:
        return
    profile = resolve_profile(profile)
    if not profile.minimum_environments <= len(environments) <= profile.maximum_environments:
        raise ValueError(f'{profile.id} needs {profile.minimum_environments}..{profile.maximum_environments} explicit environments')
    if profile.fixed_builds:
        if stability < profile.stability_window:
            raise ValueError(f'{profile.id} requires stability_window >= {profile.stability_window}')
        if any(e.server_spec.type != 'local' and e.server_spec.build is None for e in environments):
            raise ValueError('strict requires a fixed official server build for every environment')
