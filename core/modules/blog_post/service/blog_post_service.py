from core.models import BlogPost
from core.services import SluggedCrudService


class BlogPostService(SluggedCrudService):
    model = BlogPost
    slug_source = "title"
