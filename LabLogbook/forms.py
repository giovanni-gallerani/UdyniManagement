from django import forms
from LabLogbook.models import Comment, CommentContent

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['type']

class CommentContentForm(forms.ModelForm):
    class Meta:
        model = CommentContent
        fields = ['text']