# Generated migration for problem review fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_jobprogresshistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='problem',
            name='needs_review',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Flag if test cases pass locally but fail on actual platform'
            ),
        ),
        migrations.AddField(
            model_name='problem',
            name='review_notes',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='Admin notes about test case issues or review status'
            ),
        ),
        migrations.AddField(
            model_name='problem',
            name='verified_by_admin',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Whether test cases have been verified by admin'
            ),
        ),
        migrations.AddField(
            model_name='problem',
            name='reviewed_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text='Timestamp when admin reviewed the problem'
            ),
        ),
        migrations.AddIndex(
            model_name='problem',
            index=models.Index(fields=['needs_review', 'is_deleted', '-created_at'], name='problem_needs_review_idx'),
        ),
        migrations.AddIndex(
            model_name='problem',
            index=models.Index(fields=['verified_by_admin', 'is_deleted', '-created_at'], name='problem_verified_idx'),
        ),
    ]
