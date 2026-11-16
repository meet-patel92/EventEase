from django.db import migrations


DEFAULT_CATEGORIES = (
    ("Technology", "Technology talks, workshops, and product events."),
    ("Business", "Business events, entrepreneurship, and professional learning."),
    ("Education", "Classes, lectures, and learning experiences."),
    ("Music", "Concerts, live music, and performances."),
    ("Arts & Culture", "Art, heritage, exhibitions, and cultural programs."),
    ("Sports", "Sports, fitness, and active community experiences."),
    ("Health & Wellness", "Health, wellbeing, and mindful experiences."),
    ("Food & Drink", "Food festivals, tastings, and culinary events."),
    ("Networking", "Professional networking and industry gatherings."),
    ("Community", "Neighborhood gatherings and civic programs."),
    ("Other", "Events that do not fit another category."),
)


def create_missing_categories(apps, schema_editor):
    EventCategory = apps.get_model("events", "EventCategory")
    database = schema_editor.connection.alias
    for name, description in DEFAULT_CATEGORIES:
        exists = EventCategory.objects.using(database).filter(name__iexact=name).exists()
        if not exists:
            EventCategory.objects.using(database).create(
                name=name,
                description=description,
            )


class Migration(migrations.Migration):
    dependencies = [("events", "0005_event_poster_alter_event_slug")]

    operations = [
        migrations.RunPython(create_missing_categories, migrations.RunPython.noop),
    ]
