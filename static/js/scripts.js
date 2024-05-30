/* 
Edit Text with examples and links
FROM HTML call: editLinks or editText(text, id)
*/
const SPLIT_EXAMPLES = '~';

function findExamples(text){
    /*
    returns a vector with main text as string
        than a vector with all examples
    NO EXAMPLES:
        examples-vector is empty
    NO MAIN TEXT:
        main-text string is empty
    */

    // returns [''] if no match else ['match']
    const main_text = text.match(`[^${SPLIT_EXAMPLES}]*`);
    // returns [] if no match else [['notInterested', 'match1'], ...]
    const examples = [...text.matchAll(`${SPLIT_EXAMPLES}([^${SPLIT_EXAMPLES}]*)`)];
    return [main_text[0], examples.length > 0 ? examples.map(ex => ex[1]) : []]
}

function* findLinks(text){
    /* every iteration is either a link or text */
    
    // returns a vector of 4D vectors: [['notInterested', 'pre@1', '@1', 'post@1'], ...]
    const slices = [...text.matchAll('([^@]*)@([^ ]+)([^@]*)')];

    if (slices.length === 0) {
        yield [text, 'text']
    }
    else {
        for (const slice of slices){
            if (slice[1]) {
                yield [slice[1], 'text']
            }
            if (slice[2]) {
                yield [slice[2], 'link']
            }
            if (slice[3]) {
                yield [slice[3], 'text']
            }
        }
    }
}

function editLinks(text, id=null, node=null){
    if (id != null) {
        node = document.getElementById(id)
    }

    for (const slice of findLinks(text)) {
        if (slice[1] === 'link') {
            const link_word = slice[0].replaceAll('_', ' ');
            const link = document.createElement('a');
            if (link_word in REFERENCED) {
                if (REFERENCED[link_word].bool) {
                    link.classList.add('text-orange');
                }
                else {
                    link.classList.add('text-danger');
                }
            }
            else {
                node.innerHTML += slice[0];
                continue;
            }
            // should execute only if link_word in REFERNCED
            link.href = REFERENCED[link_word].link;
            link.innerHTML = link_word;
            node.appendChild(link);
        }
        else {
            node.innerHTML += slice[0]
        }
    }
}

function editText(text, id){
    /*
    edits text with examples: ~ and links: @ 
    */
    const parent = document.getElementById(id);
    const text_examples = findExamples(text);
    if (text_examples[0]) {
        const p_text = document.createElement('p');
        // main text
        p_text.classList.add('fw-medium');
        editLinks(text_examples[0], undefined, p_text);
        parent.appendChild(p_text);
    }
    if (text_examples[1].length > 0) {
        // examples
        const p_example = document.createElement('p');
        p_example.classList.add('fst-italic');
        const icon = document.createElement('i');
        icon.classList.add('bi', 'bi-dot');
        p_example.appendChild(icon);
        for (const example of text_examples[1]) {
            editLinks(example, undefined, p_example);
        }
        parent.appendChild(p_example);
    } 
}

/*
Create new instance from blueprint
newInstance needs a hidden html marked with blueprint class
it adds this content before the blueprint replacing #number with second last number+1
*/

function makeInstance(instance, dic){
    for (const key in dic) {
        instance.innerHTML = instance.innerHTML.replaceAll(key, dic[key]);
    }
}

function newInstanceStep(parent_id){
    const parent = document.getElementById(parent_id);
    // starts from 0; doesnt count botton and blueprint
    const last_instance_number = parent.children.length - 3;
    const blueprint = parent.querySelector(':scope > .blueprint');
    const new_instance = blueprint.cloneNode(true);
    new_instance.classList.remove('blueprint');
    makeInstance(new_instance, {['#number-'+parent_id+'#']: last_instance_number+1, ['#'+parent_id+'#']: ''});
    blueprint.before(new_instance);
    return last_instance_number+1;
}

function newInstance(...parent_id){
    const numbers = new Array(parent_id.length);
    for (const [i, id] of parent_id.entries()) {
        let instance_id = id;
        for (let j=i-1; j>=0; j--) {
            instance_id = instance_id.replaceAll('#number-'+parent_id[j]+'#', numbers[j]);
        }
        numbers[i] = newInstanceStep(instance_id);
    }
}

function editTemplateIterative(id, object_list){
    // object_list = ['', ...] or [{'': '', '': [...]}...]
    let blueprint = undefined;
    const children = new Array(object_list.length);
    for (const [number, element] of object_list.entries()) {
        let content = undefined;
        if (blueprint == undefined) {
            // should be executed once
            blueprint = document.getElementById(id).querySelector(':scope > .blueprint').cloneNode(true);
            blueprint.classList.remove('blueprint');
        }
        const child = blueprint.cloneNode(true);

        if (typeof element === 'object') {
            for (const innerKey in element) {
                if (typeof element[innerKey] === 'object') {
                    const id_child = id+'-#number-'+id+'#-'+innerKey
                    const fatherChild = child.querySelector('#'+CSS.escape(id_child));
                    fatherChild.prepend(...editTemplateIterative(id_child, element[innerKey]));
                }
                else {
                    // typeof element === 'string': should be executed once
                    content = element[innerKey];
                }
            }
        }
        else {
            content = element;
        }
        makeInstance(child, {['#'+id+'#']: content, ['#number-'+id+'#']: number});
        children[number] = child;
    }
    return children;
}

function editTemplate(id, object_list){
    document.getElementById(id).prepend(...editTemplateIterative(id, object_list));
}