from apps.events.analytics import timeline_summary


def user_activity_summary(user):
    return {"events": timeline_summary(user)}
