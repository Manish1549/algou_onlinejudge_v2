from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from django.conf import settings
import os 
import subprocess
from pathlib import Path
from compiler.models import Codesubmission,Problem,Testcases
import uuid
from django.contrib.auth.decorators import login_required
import google.generativeai as genai
from dotenv import load_dotenv
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re
import requests
load_dotenv()



def run_code(language, code, input_data):
    # Add debug output
    print(f"DEBUG: URL being used: {repr(settings.RUN_CODE_SERVICE_URL)}")

    try:
        payload ={
             'language': language,
             'code': code,
             'input_data': input_data
        }
        response = requests.post(
            settings.RUN_CODE_SERVICE_URL,
            json=payload,
            timeout=10  # 10 second timeout
        )
        if response.status_code == 200:
            result = response.json()
            stdout = result.get('stdout', '')
            stderr =result.get('stderr', '')
            compile_error= result.get('compile_error', False)
            return stdout, stderr, compile_error

    except requests.exceptions.Timeout:
        return "", "Run service timeout (10s)", True
    except requests.exceptions.ConnectionError:
         return "", "Cannot connect to run service", True
    except requests.exceptions.RequestException as e:
         return "", f"Run service error: {str(e)}", True
    except json.JSONDecodeError:
        return "", "Invalid response from run service", True
       
    
genai.configure(api_key=os.getenv("API_KEY"))

# Create your views here.
@login_required
@csrf_exempt
def ai_review(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    last_submission = Codesubmission.objects.filter(
        user=request.user, 
        problem=problem
    ).order_by('-timestamp').first()
    
    if not last_submission:
        return HttpResponse("No previous Submission Found")
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Please review this coding problem solution and provide constructive feedback in 3-5 bullet points. 
    Format your response with clear bullet points using '-' prefix for each point.
    
    Problem Description:
    {problem.description}
    
    User's Solution (in {last_submission.language}):
    {last_submission.code}

    Error (if any):
    {last_submission.error if last_submission.error else 'No errors reported'}
    
    Please structure your feedback to cover:
    - Code quality assessment
    - Potential improvements  
    - Alternative approaches
    - Performance considerations (including time and space complexity analysis)
    
    Keep each bullet point concise and focused.
    """
    
    response = model.generate_content(prompt)
    
    # Better response parsing
    feedback_text = response.text.strip()
    
    # Extract bullet points more reliably
    bullet_points = []
    lines = feedback_text.split('\n')
    
    for line in lines:
        line = line.strip()
        # Look for bullet indicators: -, *, •, or numbered points
        if (line.startswith('-') or line.startswith('*') or 
            line.startswith('•') or re.match(r'^\d+\.', line)):
            bullet_points.append(line)
        # Also capture lines that might be part of bullet points without markers
        elif bullet_points and not line.startswith(('#', '---', '===')):
            # Append to last bullet point if it's continuation
            bullet_points[-1] += ' ' + line
    
    # If no bullet points found, use the entire response
    if not bullet_points:
        bullet_points = [feedback_text]
    
    # Extract complexity information from feedback
    time_complexity = "O(n)"
    space_complexity = "O(1)"
    performance_grade = "A"
    
    for point in bullet_points:
        lower_point = point.lower()
        if "time complexity" in lower_point:
            if "o(1)" in lower_point or "constant" in lower_point:
                time_complexity = "O(1)"
                performance_grade = "A+"
            elif "o(log n)" in lower_point or "logarithmic" in lower_point:
                time_complexity = "O(log n)"
                performance_grade = "A"
            elif "o(n)" in lower_point or "linear" in lower_point:
                time_complexity = "O(n)"
                performance_grade = "B"
            elif "o(n log n)" in lower_point or "linearithmic" in lower_point:
                time_complexity = "O(n log n)"
                performance_grade = "C"
            elif "o(n²)" in lower_point or "quadratic" in lower_point:
                time_complexity = "O(n²)"
                performance_grade = "D"
            elif "o(2^n)" in lower_point or "exponential" in lower_point:
                time_complexity = "O(2^n)"
                performance_grade = "F"
        
        if "space complexity" in lower_point:
            if "o(1)" in lower_point or "constant" in lower_point:
                space_complexity = "O(1)"
            elif "o(n)" in lower_point or "linear" in lower_point:
                space_complexity = "O(n)"
            elif "o(n²)" in lower_point or "quadratic" in lower_point:
                space_complexity = "O(n²)"
    
    context = {
        "last_submission": last_submission,
        "problem": problem,
        "feedback_text": feedback_text,
        "bullet_points": bullet_points,
        "time_complexity": time_complexity,
        "space_complexity": space_complexity,
        "performance_grade": performance_grade,
        "quality_score": "8.5/10",
        "issues_found": "2",
        "best_practices_score": "7/10",
    }
    
    return render(request, 'ai_review.html', context)
 



@login_required
def submit(request,problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    last_submission = Codesubmission.objects.filter(user=request.user,problem=problem).order_by('-timestamp').first()
    if request.method == "POST":
        
        user_name = request.user
        language = request.POST.get('language')
        code = request.POST.get('code')
        testcases = problem.testcases_set.all()
        problem_name = problem

        results =[]
        all_passed = True     
        test_num =1
        error =''
        compile_error = False
        for testcase in testcases :
            input_data = testcase.input_data
            output_data,error,compile_error = run_code(language,code,input_data)
            
            if error.strip() :
                  if compile_error:
                      verdict ='CE'
                      results.append("Compilation Error !")
                      error = error
                      break
                  print("Compilation Successful\n")
                  verdict='RE'
                  error = error
                  results.append(f"Runtime Error on Testcase {test_num}")
                  all_passed = False
                  break
            if output_data.strip() != testcase.expected_output.strip():
                results.append(f"Testcase {test_num} failed")
                error = f"Expected {testcase.expected_output.strip()} but got {output_data}"
                verdict = 'WA'
                all_passed = False
                break
            else :
                 results.append(f"Testcase {test_num} Passed")
                 
                 
            test_num+=1

        if all_passed :
            verdict = 'AC'
        
        
         
        #save to db
        submission = Codesubmission.objects.create(
            problem = problem_name,
            user = user_name,
            language =  language,
            code = code,
            input_data = input_data,
            output_data = "\n".join(results),
            verdict = verdict,
            error = error
        )
        submission.save()
        return render(request,'compiler.html',{"submission" : submission,"problem" :problem,"last_submission":submission})
    #get 
    return render(request,'compiler.html',{"problem":problem,"last_submission":last_submission})





def problem_list(request):
    problems = Problem.objects.all()
    return render(request, 'problem_list.html', {'problems': problems})



@csrf_exempt
@login_required
def run_custom(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            language = data.get('language')
            code = data.get('code')
            input_data = data.get('input_data')
            
            output_data, error, compile_error = run_code(language, code, input_data)
            
            return JsonResponse({
                'output': output_data,
                'error': error
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


              
