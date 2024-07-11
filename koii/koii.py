import commune as c
import os
import streamlit as st


class Koii(c.Module):
    def __init__(self):
        print("Koii created")
        self.task_dirpath = self.dirpath() + '/tasks'

    def task_paths(self):
        print("Koii tasks")
        return c.ls(self.task_dirpath)
    
    def tasks(self):
        return [f.split('/')[-1] for f in self.task_paths()]
    def task2path(self, task_name = None):
        task2path =  {f.split('/')[-1]: f for f in self.task_paths()}
        if task_name:
            return task2path[task_name]
        return task2path
    
    def get_task_files(self, task_name, avoid_terms=['node_modules', 'dist/', 'build/', 'lib/'] ):
        task_path = self.task2path(task_name)
        task_paths = c.glob(task_path)
        task_js_paths = [f for f in task_paths if f.endswith('.js') if not any([term in f for term in avoid_terms])]
        return task_js_paths
    
    def task2code(self, task_name):
        task_js_files = self.get_task_files(task_name)
        task2code = {}
        for f in task_js_files:
            with open(f, 'r') as file:
                task2code[f] = file.read()
        
        return task2code
    
    def new_task(self, 
                 task_name = 'new_task', 
                 template_task = 'ez', 
                 update = False,
                 file_seperator = '__FILE__',
                 description='add 2 numbers using the following task'):
        task_code = self.task2code(template_task)
        model = c.module('model.openrouter')()

        instructions=f'''
        create a new task (rewrite the submission.js and audit.js files), 
        seperate the code by {file_seperator}
        if you import any files, make sure to include them in the outputs
        
        '''
        new_task_dirpath = self.task_dirpath + '/' + task_name
        request = c.python2str({
            'name': task_name,
            'description': description,
            'instructions': instructions,
            'example': task_code,
            'output': {
                'task/submission.js': 'str', 
                'task/audit.js': 'str',
                'tests/unitTest.js': 'str: test both the submission and the audit',
                '**': 'str: any other files you need to include in the task',
            }
        })


        filemap = ['']
        k = f'cached_tasks/{task_name}/{c.hash(request)}'
        text = self.get(k, None, update=update)
        if text == None:
            text = ''
            stream =  model.generate(request, stream=1)
            for response in stream:
                text += response
            self.put(k, text)

        filemap = {}
        for filecode in text.split(file_seperator):
            filename = filecode.split('\n')[0].strip()
            if ' ' in filename or filename == '':
                continue
            filemap[filename] = '\n'.join(filecode.split('\n')[1:])
        task_new_dirpath = self.task_dirpath + '/' + task_name + '/task'
        os.makedirs(task_new_dirpath, exist_ok=True)
        files_saved = []
        st.write(filemap.keys())
        for file, code in filemap.items():
            path = task_new_dirpath + '/' + file
            if '/' in file:
                os.makedirs(os.path.dirname(path), exist_ok=True)
            files_saved.append(path)
            code = code.split('```')[1]
            if code.startswith('javascript'):
                code = code[len('javascript'):]
            with open(path, 'w') as f:
                print('writing', path)
                f.write(code)
            
        return {'task_name': task_name, 'files_saved': files_saved, 'path': task_new_dirpath}    
    

    def task_app(self):
        st.title('Koii Task')
        task_name = st.selectbox('Task Name', self.tasks())
        task_code = self.task2code(task_name)
        delete_task = st.button('Delete Task')
       
        for file, code in task_code.items():
            with st.expander(file):
                st.code(code)
        
        if delete_task:
            c.rm(self.task2path(task_name))
            st.write(f'{task_name} deleted')
        
        

    def app(self):
        names = ['Task', 'Generate Task']
        tabs = st.tabs( names)
        for i, tab in enumerate(tabs):
            tab_name = names[i]
            with tab:
                if tab_name == 'Task':
                    self.task_app()
                if tab_name == 'Generate Task':
                    self.generate_task_app()

    def generate_task_app(self):
        st.title('Koii Task Generate')
        task_name = st.text_input('Task Name', 'new_task')
        tasks = self.tasks()
        template_task = st.selectbox('Template Task', tasks)
        description = st.text_area('Description', 'add 2 numbers using the following task')
        new_task = st.button('New Task')
        update = st.checkbox('Update')
    
        if new_task:
            with st.spinner('Creating new task'):
                response = self.new_task(task_name=task_name, 
                                         update=update,
                                         template_task=template_task,
                                           description=description)
                paths = response['files_saved']
                st.write(response['task_name'])
                for path in paths:
                    with st.expander(path):
                        st.code(c.get_text(path))

Koii.run()