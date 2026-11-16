from django.db import migrations, models
PREFIX = "[DEMO] "


def remove_demo_prefix(apps, schema_editor):
    EventCategory = apps.get_model("events", "EventCategory")
    database = schema_editor.connection.alias
    categories = EventCategory.objects.using(database).filter(name__istartswith=PREFIX)
    changes = [(category.pk, category.name, category.name[len(PREFIX):]) for category in categories]

    for category_id, _old_name, new_name in changes:
        EventCategory.objects.using(database).filter(pk=category_id).update(name=new_name)


def restore_demo_prefix(apps, schema_editor):
    EventCategory = apps.get_model("events", "EventCategory")
    Event = apps.get_model("events", "Event")
    database = schema_editor.connection.alias
    # Demo seed events identify precisely the category rows renamed forward.
    category_ids = Event.objects.using(database).filter(
        slug__startswith="demo-event-", category_id__isnull=False
    ).values_list("category_id", flat=True).distinct()
    for category in EventCategory.objects.using(database).filter(pk__in=category_ids):
        prefixed_name = f"{PREFIX}{category.name}"
        category.name = prefixed_name
        category.save(update_fields=["name"], using=database)


class Migration(migrations.Migration):
    dependencies = [("events", "0006_seed_default_categories")]

    operations = [
        migrations.AlterField(
            model_name="eventcategory",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.RunPython(remove_demo_prefix, restore_demo_prefix),
    ]
