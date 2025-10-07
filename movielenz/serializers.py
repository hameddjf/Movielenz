from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from drf_polymorphic.serializers import PolymorphicSerializer

from .models import Genre, Movie, Series, Type 

from celebrity.models import Actor, Director
from celebrity.serializers import ActorSerializer, DirectorSerializer

# --- Serializers for related models ---
class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['name', 'translated_genre','slug']
        read_only_fields = ['slug']

# --- Base Movie Serializer (non-polymorphic, for specific movie endpoints or as a base) ---
class TypeSerializer(serializers.ModelSerializer):
    parent_slug = serializers.SlugRelatedField(slug_field='slug', read_only=True, source='parent')

    class Meta:
        model = Type
        fields = ['name', 'parent_slug', 'slug']

class BaseMovieSerializer(serializers.ModelSerializer):
    # Read-only fields for related objects (full representation)
    genres = GenreSerializer(many=True, read_only=True)
    actors = ActorSerializer(many=True, read_only=True)
    directors = DirectorSerializer(many=True, read_only=True)
    type = TypeSerializer(read_only=True)

    genres_slugs = serializers.SlugRelatedField(
        queryset=Genre.objects.all(), slug_field='slug', source='genres',
        many=True, write_only=True, required=False
    )
    actors_ids = serializers.PrimaryKeyRelatedField(
        queryset=Actor.objects.all(), source='actors',
        many=True, write_only=True, required=False
    )
    directors_ids = serializers.PrimaryKeyRelatedField(
        queryset=Director.objects.all(), source='directors',
        many=True, write_only=True, required=False
    )

    object_type = serializers.CharField(read_only=True) 

    class Meta:
        model = Movie 
        fields = [
            'title', 'slug', 'type', 'object_type',
            'release_date',
            'actors', 'directors', 'description',
            'directors_ids', 'actors_ids',
            'genres', 'duration',
            'poster', 'trailer', 'production_country', 'language', 'network',
            'is_dubbed', 'is_subtitled',
            'genres_slugs',
        ]
        read_only_fields = ('slug', 'type', 'object_type')
        extra_kwargs = {
            field: {'required': False, 'allow_null': True}
            for field in ['release_date', 'description', 'imdb_id', 'tmdb_id', 'imdb_rating',
                          'duration', 'poster', 'trailer', 'production_country', 'language',
                          'network', 'tmdb_user_score', 'tmdb_popularity']
        }
        extra_kwargs['title'] = {'required': True} 

    def validate_title(self, value):
        if len(value) < 2: 
            raise serializers.ValidationError(_("Title must be at least 2 characters long."))
        return value

class MovieOnlySerializer(BaseMovieSerializer): 
    class Meta(BaseMovieSerializer.Meta):
        model = Movie

class SeriesSerializer(BaseMovieSerializer):
    class Meta(BaseMovieSerializer.Meta):
        model = Series
        fields = BaseMovieSerializer.Meta.fields + [ 
            'number_of_seasons', 'episode_count', 'series_status'
        ]
