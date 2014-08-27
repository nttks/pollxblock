/* Javascript for PollXBlock, edit view. */
function PollXBlockEdit(runtime, element) {

    /* Html element used to alert users, in case of an error */
    $('.xblock-editor-error-message', element).css('display', 'none');
    $('.xblock-editor-error-message', element).css('color', 'red');

    /* Click event for Cancel button, while in the edit mode */
    $(element).find('.cancel-button').bind('click', function() {
        runtime.notify('cancel', {});
    });

    /* Click event for Save button, while in the edit mode */
    /* Gets all the input values and sends them back to model */
    $(element).find('.save-button').bind('click', function() {

        /* Get answers */
        answerIds = [];
        answerTexts = [];
        nAnswers = $(element).find('input[id=edit_number_of_answers]').val();

        var answerId, answerText;

        for (var i=1;i<=nAnswers;i++){
            answerIdElement = $(element).find('input[name=answer'+i+'_id]');
            if (!(ValidateNotEmpty(answerIdElement, element, "ID of Answer " + i))) {
                return false;
            }
            answerIds.push(answerIdElement.val());

            answerTextElement = $(element).find('input[name=answer'+i+'_text]');
            if (!(ValidateNotEmpty(answerTextElement, element, "Text of Answer " + i))) {
                return false;
            }
            answerTexts.push(answerTextElement.val());
        }

        /* Data for the model */
        var data = {
            'display_name': $('.edit-display-name', element).val(),
            'question': $('.edit-question', element).val(),
            'answerIds': answerIds,
            'answerTexts': answerTexts,
            'reset': $('.edit-reset', element).is(':checked')
        };

        /* AJAX call and its handler */
        var handlerUrl = runtime.handlerUrl(element, 'save_edit');
        $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
            if (response.result === 'success') {
                window.location.reload(true);
            } else {
                $('.xblock-editor-error-message', element).html('Error: '+response.message);
                $('.xblock-editor-error-message', element).css('display', 'block');
            }
        });
    });

    /* Check the validity of data in text box for editing number of available answers
       when user chooses to enter the data from keyboard */
    $(element).on('keyup', 'input#edit_number_of_answers', function(){
        ValidateNumericData(this, element, "Number of answers", 2, 20);
        GenerateDynamicInputs(element, this);
    });

    /* Dynamically recreates html text inputs for answers in case user chooses to interact with the control using up and down buttons */
    $(element).on('change', 'input#edit_number_of_answers', function(){
        GenerateDynamicInputs(element, this);
    });

    function ValidateNotEmpty(stringElement, element, name) {
        var strValue = $(stringElement).val();

        if (strValue.length == 0) {
            $('.xblock-editor-error-message', element).html(name + ' is required.');
            $('.xblock-editor-error-message', element).css('display', 'block');
            $(stringElement).focus();
            return false;
        } else {
            $('.xblock-editor-error-message', element).css('display', 'none');
            return true;
        }
    }

    /*
        Validates data entered within numeric html input field
        Parameters: -validated html input element
                    -XBlock element sent from server side
                    -description name of the validated element
                    -minimum value
                    -maximum value
    */
    function ValidateNumericData(numericElement, element, name, minValue, maxValue) {
        var nmbValue = $(numericElement).val();

        if (nmbValue < minValue) {
            $('.xblock-editor-error-message', element).html(name + ' must be a positive number.');
            $('.xblock-editor-error-message', element).css('display', 'block');
            nmbValue = minValue;
        } else if (nmbValue > maxValue) {
            $('.xblock-editor-error-message', element).html('Maximum ' + name.toLowerCase() + ' is ' + maxValue + '.');
            $('.xblock-editor-error-message', element).css('display', 'block');
            nmbValue = maxValue;
        } else {
            $('.xblock-editor-error-message', element).css('display', 'none');
        }

        $(numericElement).val(nmbValue);
    }

    /* Generates label and inputs for each answer, depending on the entered number of available answers */
    function GenerateDynamicInputs(element, answerElement) {
        var nAnswers = $(answerElement).val();

        var html_String = "<label class='label setting-label'>Answer</label><label class='label setting-label group-id' id='label_id'>ID</label><label class='label setting-label group-text' id='label_text'>Text</label><span style='margin-left: 4px;' class='tip setting-help'>ID example: yes<br/>Text example: Yes</span>";
        var answerId, answerText;

        for (var i=1;i<=nAnswers;i++){

            answerId = $(element).find('input[name=answer'+i+'_id]').val();
            answerText = $(element).find('input[name=answer'+i+'_text]').val();

            if (answerId == null){
                html_String += "<p><label class='label setting-label'>Answer "+i+"</label><input style='margin-left: 4px;' class='input setting-input group-id' name='answer"+i+"_id' id='answer"+i+"_id' value='' type='text'>";
            }
            else{
                html_String += "<p><label class='label setting-label'>Answer "+i+"</label><input style='margin-left: 4px;' class='input setting-input group-id' name='answer"+i+"_id' id='answer"+i+"_id' value='"+answerId+"' type='text'>";
            }

            if (answerText == null){
                html_String += "<input style='margin-left: 4px;' class='input setting-input group-text' name='answer"+i+"_text' id='answer"+i+"_text' value='' type='text'></p>";
            }
            else{
                html_String += "<input style='margin-left: 4px;' class='input setting-input group-text' name='answer"+i+"_text' id='answer"+i+"_text' value='"+answerText+"' type='text'></p>";
            }
        }

        $("#panel2", element).html(html_String);
    }

    $(function ($) {
        // Manually runs polyfill for input number types to correct for Firefox non-support.
        if ($.fn.inputNumber) {
            $(element).find('.setting-input-number').inputNumber();
        }
    });
}
