from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.text import slugify


class User(AbstractUser):
    pass


class Character(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Comic(models.Model):
    title = models.CharField(
        max_length=255,
        validators=[RegexValidator(r'\S', 'A title must contain a non-whitespace character.')],
    )
    image = models.ImageField(upload_to='comics/')
    slug = models.SlugField(max_length=255, unique=True, blank=True, editable=False)
    panel_count = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    creator_credit = models.CharField(max_length=255, blank=True)
    found_at = models.URLField(
        blank=True,
        help_text='Where the current image copy was found; not necessarily its origin.',
    )
    characters = models.ManyToManyField(Character, blank=True, related_name='comics')
    tags = models.ManyToManyField(Tag, blank=True, related_name='comics')

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(panel_count__gte=1) | models.Q(panel_count__isnull=True),
                name='comic_panel_count_positive',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            prefix = slugify(self.title)[:222].strip('-') or 'comic'
            self.slug = f'{prefix}-{uuid4().hex}'
        super().save(*args, **kwargs)

