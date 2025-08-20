from django.urls import path, include
from compiler.views import submit,problem_list,ai_review,run_custom

urlpatterns = [
    path('problems/',problem_list,name='problems'),
    path('problems/<int:problem_id>/',submit,name = 'submit'),
    path('problems/<int:problem_id>/ai-review/',ai_review,name='ai_review'),
    path('run_custom/', run_custom, name='run_custom'),
    path('run_custom', run_custom, name='run_custom_no_slash')  # Without slash
]